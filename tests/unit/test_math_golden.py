"""Unit tests for math layer with golden file comparisons."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

from hypothesis import given
from hypothesis import strategies as st

from ledzephyr.metrics import MetricsCalculator
from ledzephyr.models import TeamSource, TestCaseModel


class TestMathGolden:
    """Golden file tests for mathematical calculations."""

    def test_calculate_metrics_basic_golden(self, mock_api_client):
        """Test metrics calculation against golden output file."""
        # Arrange
        calculator = MetricsCalculator(mock_api_client)

        # Load golden input data
        fixtures_dir = Path(__file__).parent.parent.parent / "testdata" / "fixtures"
        with open(fixtures_dir / "math_input_basic.json") as f:
            input_data = json.load(f)

        # Convert JSON to TestCaseModel objects
        test_cases = []
        for tc_data in input_data["test_cases"]:
            # Convert ISO strings to datetime objects
            created = datetime.fromisoformat(tc_data["created"].replace("Z", "+00:00"))
            updated = datetime.fromisoformat(tc_data["updated"].replace("Z", "+00:00"))
            last_execution = None
            if tc_data["last_execution"]:
                last_execution = datetime.fromisoformat(
                    tc_data["last_execution"].replace("Z", "+00:00")
                )

            test_case = TestCaseModel(
                id=tc_data["id"],
                key=tc_data["key"],
                summary=tc_data["summary"],
                project_key=tc_data["project_key"],
                component=tc_data["component"],
                labels=tc_data["labels"],
                assignee=tc_data["assignee"],
                source_system=tc_data["source_system"],
                created=created,
                updated=updated,
                status=tc_data["status"],
                last_execution=last_execution,
                execution_status=tc_data["execution_status"],
            )
            test_cases.append(test_case)

        # Separate by source system
        zephyr_tests = [tc for tc in test_cases if tc.source_system == "zephyr"]
        qtest_tests = [tc for tc in test_cases if tc.source_system == "qtest"]

        # Mock the API client methods
        mock_api_client.get_jira_project.return_value = Mock(
            key=input_data["project_key"], name="Demo Project"
        )
        mock_api_client.get_zephyr_tests.return_value = zephyr_tests
        mock_api_client.get_qtest_tests.return_value = qtest_tests
        mock_api_client.get_test_executions.return_value = {}

        # Act
        result = calculator.calculate_metrics(
            input_data["project_key"], input_data["time_window"], TeamSource.COMPONENT
        )

        # Load expected golden output
        with open(fixtures_dir / "math_output_golden.json") as f:
            expected = json.load(f)

        # Assert core metrics match golden file
        assert result.project_key == expected["project_key"]
        assert result.time_window == expected["time_window"]
        assert result.total_tests == expected["total_tests"]
        assert result.zephyr_tests == expected["zephyr_tests"]
        assert result.qtest_tests == expected["qtest_tests"]
        assert abs(result.adoption_ratio - expected["adoption_ratio"]) < 0.001
        assert result.active_users == expected["active_users"]
        assert abs(result.coverage_parity - expected["coverage_parity"]) < 0.001
        assert abs(result.defect_link_rate - expected["defect_link_rate"]) < 0.001

    def test_adoption_ratio_calculation_golden(self):
        """Test adoption ratio calculation with known values."""
        # Test cases from golden data
        test_cases = [
            (0, 0, 0.0),  # No tests
            (10, 0, 0.0),  # Only Zephyr
            (0, 10, 1.0),  # Only qTest
            (5, 5, 0.5),  # Equal split
            (2, 8, 0.8),  # qTest majority
            (9, 1, 0.1),  # Zephyr majority
        ]

        for zephyr_count, qtest_count, expected_ratio in test_cases:
            total = zephyr_count + qtest_count
            if total == 0:
                result = 0.0
            else:
                result = qtest_count / total

            assert abs(result - expected_ratio) < 0.001, (
                f"Failed for zephyr={zephyr_count}, qtest={qtest_count}: "
                f"expected {expected_ratio}, got {result}"
            )


class TestMathProperties:
    """Property-based tests for mathematical invariants."""

    @given(
        zephyr_count=st.integers(min_value=0, max_value=1000),
        qtest_count=st.integers(min_value=0, max_value=1000),
    )
    def test_adoption_ratio_properties(self, zephyr_count, qtest_count):
        """Test adoption ratio mathematical properties."""
        total = zephyr_count + qtest_count

        if total == 0:
            adoption_ratio = 0.0
        else:
            adoption_ratio = qtest_count / total

        # Invariants
        assert 0.0 <= adoption_ratio <= 1.0

        if qtest_count == 0:
            assert adoption_ratio == 0.0
        if zephyr_count == 0 and qtest_count > 0:
            assert adoption_ratio == 1.0
        if zephyr_count == qtest_count and total > 0:
            assert abs(adoption_ratio - 0.5) < 0.001

    @given(
        users=st.lists(
            st.text(
                min_size=1, max_size=50, alphabet=st.characters(min_codepoint=97, max_codepoint=122)
            ),
            min_size=0,
            max_size=100,
        )
    )
    def test_active_users_count_properties(self, users):
        """Test active user counting properties."""
        unique_users = set(users)

        # The count should equal the number of unique users
        assert len(unique_users) == len(set(users))

        # Count should be between 0 and total users
        assert 0 <= len(unique_users) <= len(users)

        # If all users are the same, count should be 1 (or 0 if empty)
        if users and all(u == users[0] for u in users):
            assert len(unique_users) == 1

    @given(
        executed_tests=st.integers(min_value=0, max_value=1000),
        total_tests=st.integers(min_value=0, max_value=1000),
    )
    def test_execution_rate_properties(self, executed_tests, total_tests):
        """Test execution rate calculation properties."""
        # Ensure executed_tests doesn't exceed total_tests
        executed_tests = min(executed_tests, total_tests)

        if total_tests == 0:
            execution_rate = 0.0
        else:
            execution_rate = executed_tests / total_tests

        # Invariants
        assert 0.0 <= execution_rate <= 1.0

        if executed_tests == 0:
            assert execution_rate == 0.0
        if executed_tests == total_tests and total_tests > 0:
            assert execution_rate == 1.0


class TestTimeWindowParsing:
    """Test time window parsing with edge cases."""

    def test_parse_time_window_golden_cases(self):
        """Test time window parsing with known good values."""
        calculator = MetricsCalculator(Mock())

        # Use a fixed end date for deterministic testing
        end_date = datetime(2025, 6, 30, 23, 59, 59)

        test_cases = [
            ("1h", 1),
            ("24h", 24),
            ("7d", 7 * 24),
            ("30d", 30 * 24),
            ("1w", 7 * 24),
            ("4w", 4 * 7 * 24),
        ]

        for window_str, expected_hours in test_cases:
            result = calculator._parse_time_window(window_str, end_date)

            # Calculate the difference in hours
            diff_hours = (end_date - result).total_seconds() / 3600

            assert abs(diff_hours - expected_hours) < 0.1, (
                f"Failed for {window_str}: expected {expected_hours} hours, "
                f"got {diff_hours:.2f} hours"
            )

    def test_parse_time_window_invalid_defaults_to_seven_days(self):
        """Test that invalid time windows default to 7 days."""
        calculator = MetricsCalculator(Mock())
        end_date = datetime(2025, 6, 30, 23, 59, 59)

        invalid_inputs = ["invalid", "abc", "", "1x", "h", "d", "w"]

        for invalid_input in invalid_inputs:
            result = calculator._parse_time_window(invalid_input, end_date)
            expected_hours = 7 * 24  # 7 days
            diff_hours = (end_date - result).total_seconds() / 3600

            assert abs(diff_hours - expected_hours) < 0.1, (
                f"Failed for invalid input '{invalid_input}': "
                f"expected {expected_hours} hours, got {diff_hours:.2f} hours"
            )
