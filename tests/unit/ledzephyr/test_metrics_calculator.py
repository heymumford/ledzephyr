"""Tests for MetricsCalculator functionality."""

from datetime import datetime, timedelta
from unittest.mock import Mock

from ledzephyr.metrics import MetricsCalculator
from ledzephyr.models import TeamSource, TestCaseModel


class TestMetricsCalculator:
    """Test the MetricsCalculator class."""

    def test_parse_time_window_hours(self):
        """Test parsing time window in hours."""
        calculator = MetricsCalculator(Mock())
        end_date = datetime(2024, 1, 15, 12, 0, 0)

        result = calculator._parse_time_window("24h", end_date)
        expected = end_date - timedelta(hours=24)

        assert result == expected

    def test_parse_time_window_days(self):
        """Test parsing time window in days."""
        calculator = MetricsCalculator(Mock())
        end_date = datetime(2024, 1, 15, 12, 0, 0)

        result = calculator._parse_time_window("7d", end_date)
        expected = end_date - timedelta(days=7)

        assert result == expected

    def test_parse_time_window_weeks(self):
        """Test parsing time window in weeks."""
        calculator = MetricsCalculator(Mock())
        end_date = datetime(2024, 1, 15, 12, 0, 0)

        result = calculator._parse_time_window("2w", end_date)
        expected = end_date - timedelta(weeks=2)

        assert result == expected

    def test_parse_time_window_invalid_defaults_to_days(self):
        """Test that invalid time window defaults to 7 days."""
        calculator = MetricsCalculator(Mock())
        end_date = datetime(2024, 1, 15, 12, 0, 0)

        result = calculator._parse_time_window("invalid", end_date)
        expected = end_date - timedelta(days=7)

        assert result == expected

    def test_calculate_coverage_parity_equal_execution(self):
        """Test coverage parity calculation with equal execution rates."""
        calculator = MetricsCalculator(Mock())

        zephyr_tests = [
            TestCaseModel(
                id="z1",
                key="Z-1",
                summary="Test 1",
                project_key="TEST",
                component="comp1",
                labels=[],
                assignee="user1",
                source_system="zephyr",
                created=datetime.now(),
                updated=datetime.now(),
                status="Done",
                last_execution=datetime.now(),
                execution_status="PASS",
            ),
            TestCaseModel(
                id="z2",
                key="Z-2",
                summary="Test 2",
                project_key="TEST",
                component="comp1",
                labels=[],
                assignee="user1",
                source_system="zephyr",
                created=datetime.now(),
                updated=datetime.now(),
                status="Done",
                last_execution=None,
                execution_status=None,
            ),
        ]

        qtest_tests = [
            TestCaseModel(
                id="q1",
                key="Q-1",
                summary="Test 1",
                project_key="TEST",
                component="comp1",
                labels=[],
                assignee="user1",
                source_system="qtest",
                created=datetime.now(),
                updated=datetime.now(),
                status="Done",
                last_execution=datetime.now(),
                execution_status="PASS",
            ),
            TestCaseModel(
                id="q2",
                key="Q-2",
                summary="Test 2",
                project_key="TEST",
                component="comp1",
                labels=[],
                assignee="user1",
                source_system="qtest",
                created=datetime.now(),
                updated=datetime.now(),
                status="Done",
                last_execution=None,
                execution_status=None,
            ),
        ]

        result = calculator._calculate_coverage_parity(zephyr_tests, qtest_tests)

        # Both have 50% execution rate, so parity should be 1.0
        assert result == 1.0

    def test_calculate_defect_link_rate(self):
        """Test defect link rate calculation."""
        calculator = MetricsCalculator(Mock())

        tests = [
            TestCaseModel(
                id="t1",
                key="T-1",
                summary="Test 1",
                project_key="TEST",
                component="comp1",
                labels=[],
                assignee="user1",
                source_system="test",
                created=datetime.now(),
                updated=datetime.now(),
                status="Done",
                last_execution=datetime.now(),
                execution_status="PASS",
                linked_defects=["BUG-1"],
            ),
            TestCaseModel(
                id="t2",
                key="T-2",
                summary="Test 2",
                project_key="TEST",
                component="comp1",
                labels=[],
                assignee="user1",
                source_system="test",
                created=datetime.now(),
                updated=datetime.now(),
                status="Done",
                last_execution=datetime.now(),
                execution_status="PASS",
                linked_defects=[],
            ),
        ]

        result = calculator._calculate_defect_link_rate(tests)

        # 1 out of 2 tests has linked defects = 50%
        assert result == 0.5

    def test_count_active_users(self):
        """Test active user counting."""
        calculator = MetricsCalculator(Mock())

        tests = [
            TestCaseModel(
                id="t1",
                key="T-1",
                summary="Test 1",
                project_key="TEST",
                component="comp1",
                labels=[],
                assignee="user1",
                source_system="test",
                created=datetime.now(),
                updated=datetime.now(),
                status="Done",
                last_execution=datetime.now(),
                execution_status="PASS",
            ),
            TestCaseModel(
                id="t2",
                key="T-2",
                summary="Test 2",
                project_key="TEST",
                component="comp1",
                labels=[],
                assignee="user2",
                source_system="test",
                created=datetime.now(),
                updated=datetime.now(),
                status="Done",
                last_execution=datetime.now(),
                execution_status="PASS",
            ),
            TestCaseModel(
                id="t3",
                key="T-3",
                summary="Test 3",
                project_key="TEST",
                component="comp1",
                labels=[],
                assignee="user1",
                source_system="test",
                created=datetime.now(),
                updated=datetime.now(),
                status="Done",
                last_execution=datetime.now(),
                execution_status="PASS",
            ),
        ]

        result = calculator._count_active_users(tests)

        # Should count unique assignees
        assert result == 2

    def test_get_team_name_by_component(self):
        """Test team name extraction by component."""
        calculator = MetricsCalculator(Mock())

        test = TestCaseModel(
            id="t1",
            key="T-1",
            summary="Test 1",
            project_key="TEST",
            component="Frontend",
            labels=["ui", "e2e"],
            assignee="user1",
            source_system="test",
            created=datetime.now(),
            updated=datetime.now(),
            status="Done",
            last_execution=datetime.now(),
            execution_status="PASS",
        )

        result = calculator._get_team_name(test, TeamSource.COMPONENT)
        assert result == "Frontend"

    def test_get_team_name_by_label(self):
        """Test team name extraction by label."""
        calculator = MetricsCalculator(Mock())

        test = TestCaseModel(
            id="t1",
            key="T-1",
            summary="Test 1",
            project_key="TEST",
            component="Frontend",
            labels=["team-alpha", "ui"],
            assignee="user1",
            source_system="test",
            created=datetime.now(),
            updated=datetime.now(),
            status="Done",
            last_execution=datetime.now(),
            execution_status="PASS",
        )

        result = calculator._get_team_name(test, TeamSource.LABEL)
        assert result == "team-alpha"

    def test_calculate_metrics_basic_project_returns_metrics(self):
        """Test calculate_metrics with basic project data returns valid metrics."""
        mock_client = Mock()
        calculator = MetricsCalculator(mock_client)

        # Mock Jira project
        mock_client.get_jira_project.return_value = Mock(key="TEST", name="Test Project")

        # Mock test cases
        mock_client.get_zephyr_tests.return_value = [
            TestCaseModel(
                id="z1",
                key="Z-1",
                summary="Zephyr Test",
                project_key="TEST",
                component="comp1",
                labels=[],
                assignee="user1",
                source_system="zephyr",
                created=datetime.now(),
                updated=datetime.now(),
                status="Done",
                last_execution=datetime.now(),
                execution_status="PASS",
            )
        ]
        mock_client.get_qtest_tests.return_value = [
            TestCaseModel(
                id="q1",
                key="Q-1",
                summary="qTest Test",
                project_key="TEST",
                component="comp1",
                labels=[],
                assignee="user2",
                source_system="qtest",
                created=datetime.now(),
                updated=datetime.now(),
                status="Done",
                last_execution=datetime.now(),
                execution_status="PASS",
            )
        ]

        # Mock executions
        mock_client.get_test_executions.return_value = {}

        result = calculator.calculate_metrics("TEST", "7d")

        assert result.project_key == "TEST"
        assert result.time_window == "7d"
        assert result.total_tests == 2
        assert result.zephyr_tests == 1
        assert result.qtest_tests == 1
        assert result.adoption_ratio == 0.5
