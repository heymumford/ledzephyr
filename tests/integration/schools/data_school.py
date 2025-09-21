"""
Data School: Data flow and transformation patterns

Orthogonal Concern: How data moves through the system
- Gold master datasets
- Metrics calculations
- Data validation
- Format conversions
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pandas as pd

from ledzephyr.metrics import MetricsCalculator
from ledzephyr.models import TestCaseModel
from migrate_specs.gold import build_gold_master

from . import Kata, School, register_school


def kata_gold_master_generation():
    """Kata: Gold master datasets generate with expected schema."""
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmp_dir:
        out_dir = Path(tmp_dir) / "gold"
        df = build_gold_master(out_dir, days=7, seed=42)

        # Schema validation
        required_cols = ["date", "zephyr_activity", "qtest_activity", "jira_issue_status"]
        for col in required_cols:
            assert col in df.columns, f"Missing column: {col}"

        # Data quality
        assert len(df) > 0, "Should have data rows"
        assert df["zephyr_activity"].min() >= 0, "Activity should be non-negative"
        assert df["qtest_activity"].min() >= 0, "Activity should be non-negative"

        # Files created
        assert (out_dir / "gold_master.csv").exists()
        assert (out_dir / "gold_master.parquet").exists()

    return True


def kata_metrics_calculation_pipeline():
    """Kata: Metrics calculator processes test data correctly."""
    # Create mock client with test data
    mock_client = Mock()
    mock_client.get_jira_project.return_value = Mock(key="TEST", name="Test Project")

    # Create test cases
    test_cases = [
        TestCaseModel(
            id="TEST-1",
            key="TEST-1",
            summary="Test case 1",
            project_key="TEST",
            component="Component1",
            labels=["automated"],
            assignee="user@example.com",
            source_system="zephyr",
            created=datetime.now(),
            updated=datetime.now(),
            status="Open",
            last_execution=datetime.now(),
            execution_status="PASS",
        ),
        TestCaseModel(
            id="TEST-2",
            key="TEST-2",
            summary="Test case 2",
            project_key="TEST",
            component="Component2",
            labels=["manual"],
            assignee="user2@example.com",
            source_system="qtest",
            created=datetime.now(),
            updated=datetime.now(),
            status="InProgress",
            last_execution=None,
            execution_status=None,
        ),
    ]

    mock_client.get_zephyr_tests.return_value = [test_cases[0]]
    mock_client.get_qtest_tests.return_value = [test_cases[1]]
    mock_client.get_test_executions.return_value = {}

    # Run calculation
    calculator = MetricsCalculator(mock_client)
    result = calculator.calculate_metrics("TEST", "7d")

    # Validate results
    assert result.project_key == "TEST"
    assert result.total_tests == 2
    assert 0 <= result.adoption_ratio <= 1

    return True


def kata_data_format_conversions():
    """Kata: System handles multiple data formats consistently."""
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmp_dir:
        out_dir = Path(tmp_dir) / "formats"
        df_original = build_gold_master(out_dir, days=3, seed=123)

        # Read back both formats
        df_csv = pd.read_csv(out_dir / "gold_master.csv")
        df_parquet = pd.read_parquet(out_dir / "gold_master.parquet")

        # Convert date for comparison
        df_csv["date"] = pd.to_datetime(df_csv["date"]).dt.date

        # Should be identical
        pd.testing.assert_frame_equal(df_csv, df_parquet)

    return True


def kata_data_validation_rules():
    """Kata: Data validation catches quality issues."""
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmp_dir:
        out_dir = Path(tmp_dir) / "validation"
        df = build_gold_master(out_dir, days=5, seed=999)

        # Quality checks that should pass
        assert df["zephyr_activity"].sum() > 0, "Should have Zephyr activity"
        assert df["qtest_activity"].sum() > 0, "Should have qTest activity"
        assert len(df["jira_issue_status"].unique()) > 1, "Should have multiple statuses"
        assert len(df["priority"].unique()) > 1, "Should have multiple priorities"
        assert len(df["date"].unique()) > 1, "Should have multiple days"

    return True


# Define the Data School
data_school = School(
    name="data_school",
    description="Data flow, transformation, and validation patterns",
    katas=[
        Kata(
            "gold_master_generation",
            "Gold master datasets generate correctly",
            kata_gold_master_generation,
        ),
        Kata(
            "metrics_calculation",
            "Metrics calculator processes data",
            kata_metrics_calculation_pipeline,
        ),
        Kata(
            "format_conversions",
            "Multiple data formats work consistently",
            kata_data_format_conversions,
        ),
        Kata(
            "validation_rules", "Data validation catches quality issues", kata_data_validation_rules
        ),
    ],
    parallel_safe=True,
)

# Register for discovery
register_school(data_school)
