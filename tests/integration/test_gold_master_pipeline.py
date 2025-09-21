"""Integration tests using gold master datasets (no live API calls)."""

from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from ledzephyr.client import APIClient
from ledzephyr.config import Config
from ledzephyr.metrics import MetricsCalculator


@pytest.mark.integration
def test_e2e_with_gold_master_csv(tmp_path):
    """Test end-to-end pipeline using gold master CSV data instead of live APIs."""
    # Arrange - ensure gold master exists
    gold_file = Path("gold/gold_master.csv")
    if not gold_file.exists():
        pytest.skip("Gold master file not found. Run 'make gold' first.")

    # Load gold master data
    gold_df = pd.read_csv(gold_file)

    # Create test config
    config = Config(
        jira_url="https://test.atlassian.net",
        jira_username="test@example.com",
        jira_api_token="test_token",
        zephyr_token="zephyr_test_token",
        qtest_url="https://test.qtestnet.com",
        qtest_token="qtest_test_token",
    )

    # Mock API responses using gold master data
    with (
        patch.object(APIClient, "get_jira_project") as mock_jira,
        patch.object(APIClient, "get_zephyr_tests") as mock_zephyr,
        patch.object(APIClient, "get_qtest_tests") as mock_qtest,
        patch.object(APIClient, "get_test_executions") as mock_executions,
    ):
        # Setup mocks based on gold master data
        mock_jira.return_value = Mock(key="GOLD", name="Gold Master Project")

        # Create test cases from gold master activity data
        mock_zephyr.return_value = _create_test_cases_from_gold(gold_df, "zephyr")
        mock_qtest.return_value = _create_test_cases_from_gold(gold_df, "qtest")
        mock_executions.return_value = {}

        # Act - run metrics calculation
        client = APIClient(config)
        calculator = MetricsCalculator(client)

        result = calculator.calculate_metrics("GOLD", "7d")

        # Assert - verify calculation completed successfully
        assert result.project_key == "GOLD"
        assert result.time_window == "7d"
        assert result.total_tests > 0
        assert 0 <= result.adoption_ratio <= 1


@pytest.mark.integration
def test_cli_with_gold_master_env_override(tmp_path, monkeypatch):
    """Test CLI integration with environment variable pointing to gold master."""
    # Arrange
    gold_file = Path("gold/gold_master.csv")
    if not gold_file.exists():
        pytest.skip("Gold master file not found. Run 'make gold' first.")

    # Set environment variable to use gold master
    monkeypatch.setenv("LEDZEPHYR_USE_GOLD_MASTER", "true")
    monkeypatch.setenv("LEDZEPHYR_GOLD_MASTER_PATH", str(gold_file.absolute()))

    # Mock the API to use gold master data
    with patch("ledzephyr.client.APIClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Load gold master data
        gold_df = pd.read_csv(gold_file)

        # Configure mocks
        mock_client.get_jira_project.return_value = Mock(key="GOLD", name="Gold Master Project")
        mock_client.get_zephyr_tests.return_value = _create_test_cases_from_gold(gold_df, "zephyr")
        mock_client.get_qtest_tests.return_value = _create_test_cases_from_gold(gold_df, "qtest")
        mock_client.get_test_executions.return_value = {}

        # Act - the actual CLI would use environment variables to switch to gold master mode
        # For this test, we're just verifying the mocking works
        from ledzephyr.config import Config
        from ledzephyr.metrics import MetricsCalculator

        config = Config(
            jira_url="https://test.atlassian.net",
            jira_username="test@example.com",
            jira_api_token="test_token",
        )

        calculator = MetricsCalculator(mock_client)
        result = calculator.calculate_metrics("GOLD", "7d")

        # Assert
        assert result.project_key == "GOLD"
        assert result.total_tests > 0


@pytest.mark.integration
def test_gold_master_data_quality():
    """Test that gold master data meets quality requirements."""
    # Arrange
    gold_file = Path("gold/gold_master.csv")
    if not gold_file.exists():
        pytest.skip("Gold master file not found. Run 'make gold' first.")

    # Act
    df = pd.read_csv(gold_file)

    # Assert - data quality checks
    required_columns = [
        "date",
        "zephyr_activity",
        "qtest_activity",
        "jira_issue_status",
        "priority",
        "has_attachment",
    ]

    for col in required_columns:
        assert col in df.columns, f"Missing required column: {col}"

    # Activity levels should be non-negative
    assert all(df["zephyr_activity"] >= 0), "Zephyr activity must be non-negative"
    assert all(df["qtest_activity"] >= 0), "qTest activity must be non-negative"

    # Should have reasonable activity levels (not all zeros)
    assert df["zephyr_activity"].sum() > 0, "Should have some Zephyr activity"
    assert df["qtest_activity"].sum() > 0, "Should have some qTest activity"

    # Should have variety in categorical factors
    assert len(df["jira_issue_status"].unique()) > 1, "Should have multiple issue statuses"
    assert len(df["priority"].unique()) > 1, "Should have multiple priorities"

    # Should have multiple days of data
    assert len(df["date"].unique()) > 1, "Should have multi-day data"


def _create_test_cases_from_gold(gold_df: pd.DataFrame, source_system: str) -> list:
    """Create mock test cases from gold master activity data."""
    from datetime import datetime

    from ledzephyr.models import TestCaseModel

    # Sample the activity data to create realistic test case counts
    activity_col = f"{source_system}_activity"
    total_activity = gold_df[activity_col].sum()

    # Create test cases proportional to activity
    test_cases = []
    for i in range(min(total_activity, 100)):  # Cap at 100 for performance
        status_sample = gold_df.sample(1).iloc[0]

        test_case = TestCaseModel(
            id=f"{source_system.upper()}-{i+1}",
            key=f"{source_system.upper()}-{i+1}",
            summary=f"Gold master test case {i+1}",
            project_key="GOLD",
            component="TestComponent",
            labels=["gold", "automated"],
            assignee=f"user{i % 5}@example.com",
            source_system=source_system,
            created=datetime.now(),
            updated=datetime.now(),
            status=status_sample["jira_issue_status"],
            last_execution=datetime.now() if i % 3 == 0 else None,
            execution_status="PASS" if i % 4 != 0 else "FAIL",
        )
        test_cases.append(test_case)

    return test_cases
