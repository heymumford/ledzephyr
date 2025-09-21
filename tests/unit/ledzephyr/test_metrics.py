"""Unit tests for metrics calculation."""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from ledzephyr.client import APIClient
from ledzephyr.metrics import MetricsCalculator
from ledzephyr.models import (
    JiraProject,
    ProjectMetrics,
    TeamMetrics,
    TeamSource,
    TestCaseModel,
    TrendData,
)


class TestMetricsCalculator:
    """Test suite for MetricsCalculator."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock API client."""
        return Mock(spec=APIClient)

    @pytest.fixture
    def calculator(self, mock_client):
        """Create a MetricsCalculator instance with mock client."""
        return MetricsCalculator(mock_client)

    @pytest.fixture
    def sample_project(self):
        """Create a sample Jira project."""
        return JiraProject(
            key="TEST",
            name="Test Project",
            description="Test project for metrics",
            components=["Backend", "Frontend", "QA"],
        )

    @pytest.fixture
    def sample_zephyr_tests(self):
        """Create sample Zephyr test cases."""
        tests = []
        for i in range(1, 61):  # 60 Zephyr tests
            test = TestCaseModel(
                id=f"Z-{i:03d}",
                key=f"Z-TC-{i:03d}",
                summary=f"Zephyr Test {i}",
                project_key="TEST",
                component="Backend" if i % 3 == 0 else "Frontend" if i % 3 == 1 else "QA",
                labels=[f"team-{i % 3}"],
                assignee=f"user{i % 5}@example.com",
                source_system="zephyr",
                created=datetime.now() - timedelta(days=30),
                updated=datetime.now() - timedelta(days=1),
                status="Active",
                linked_defects=[f"BUG-{i}"] if i % 5 == 0 else [],
            )
            tests.append(test)
        return tests

    @pytest.fixture
    def sample_qtest_tests(self):
        """Create sample qTest test cases."""
        tests = []
        for i in range(1, 41):  # 40 qTest tests
            test = TestCaseModel(
                id=f"Q-{i:03d}",
                key=f"Q-TC-{i:03d}",
                summary=f"qTest Test {i}",
                project_key="TEST",
                component="Backend" if i % 3 == 0 else "Frontend" if i % 3 == 1 else "QA",
                labels=[f"team-{i % 3}"],
                assignee=f"user{i % 5}@example.com",
                source_system="qtest",
                created=datetime.now() - timedelta(days=20),
                updated=datetime.now() - timedelta(days=1),
                status="Active",
                linked_defects=[f"BUG-{i}"] if i % 4 == 0 else [],
            )
            tests.append(test)
        return tests

    def test_calculate_metrics_basic(
        self, calculator, mock_client, sample_project, sample_zephyr_tests, sample_qtest_tests
    ):
        """Test basic metrics calculation."""
        # Setup mocks
        mock_client.get_jira_project.return_value = sample_project
        mock_client.get_zephyr_tests.return_value = sample_zephyr_tests
        mock_client.get_qtest_tests.return_value = sample_qtest_tests
        mock_client.get_test_executions.return_value = {}  # Empty dict, not list

        # Calculate metrics
        result = calculator.calculate_metrics("TEST", "30d")

        # Verify API calls
        mock_client.get_jira_project.assert_called_once_with("TEST")
        # get_zephyr_tests and get_qtest_tests are called multiple times:
        # - Once for main calculation
        # - 4 times for weekly trend calculation
        assert mock_client.get_zephyr_tests.call_count == 5
        assert mock_client.get_qtest_tests.call_count == 5
        # get_test_executions is called twice for main calculation (zephyr + qtest)
        assert mock_client.get_test_executions.call_count == 2

        # Verify results
        assert isinstance(result, ProjectMetrics)
        assert result.project_key == "TEST"
        assert result.time_window == "30d"
        assert result.total_tests == 100  # 60 + 40
        assert result.zephyr_tests == 60
        assert result.qtest_tests == 40
        assert result.adoption_ratio == 0.4  # 40/100

    def test_parse_time_window(self, calculator):
        """Test time window parsing."""
        end_date = datetime.now()

        # Test days
        start = calculator._parse_time_window("7d", end_date)
        assert (end_date - start).days == 7

        # Test weeks
        start = calculator._parse_time_window("2w", end_date)
        assert (end_date - start).days == 14

        # Test plain number (days)
        start = calculator._parse_time_window("30", end_date)
        assert (end_date - start).days == 30

        # Test invalid format (defaults to 7 days)
        start = calculator._parse_time_window("invalid", end_date)
        assert (end_date - start).days == 7

    def test_calculate_coverage_parity(self, calculator, sample_zephyr_tests, sample_qtest_tests):
        """Test coverage parity calculation."""
        # Add execution data to some tests
        for i, test in enumerate(sample_zephyr_tests[:30]):
            test.last_execution = datetime.now()
            test.execution_status = "Passed" if i % 2 == 0 else "Failed"

        for i, test in enumerate(sample_qtest_tests[:20]):
            test.last_execution = datetime.now()
            test.execution_status = "Passed" if i % 2 == 0 else "Failed"

        # Calculate parity
        parity = calculator._calculate_coverage_parity(sample_zephyr_tests, sample_qtest_tests)

        # Zephyr coverage: 30/60 = 0.5
        # qTest coverage: 20/40 = 0.5
        # Parity should be 100% (both have same coverage rate)
        assert parity == 1.0

    def test_calculate_defect_link_rate(self, calculator, sample_zephyr_tests, sample_qtest_tests):
        """Test defect link rate calculation."""
        all_tests = sample_zephyr_tests + sample_qtest_tests

        # Zephyr: every 5th test has defects (12 out of 60)
        # qTest: every 4th test has defects (10 out of 40)
        # Total: 22 out of 100 = 0.22 (22%)

        rate = calculator._calculate_defect_link_rate(all_tests)
        assert rate == 0.22

    def test_count_active_users(self, calculator, sample_zephyr_tests, sample_qtest_tests):
        """Test active user counting."""
        all_tests = sample_zephyr_tests + sample_qtest_tests

        # Tests use user0 through user4, so 5 unique users
        count = calculator._count_active_users(all_tests)
        assert count == 5

    def test_calculate_team_metrics_by_component(
        self, calculator, sample_zephyr_tests, sample_qtest_tests
    ):
        """Test team metrics calculation by component."""
        all_tests = sample_zephyr_tests + sample_qtest_tests

        team_metrics = calculator._calculate_team_metrics(
            all_tests, TeamSource.COMPONENT, sample_zephyr_tests, sample_qtest_tests
        )

        # Should have 3 teams: Backend, Frontend, QA
        assert len(team_metrics) == 3
        assert "Backend" in team_metrics
        assert "Frontend" in team_metrics
        assert "QA" in team_metrics

        # Check Backend team metrics
        backend = team_metrics["Backend"]
        assert isinstance(backend, TeamMetrics)
        assert backend.team_name == "Backend"
        assert backend.team_source == TeamSource.COMPONENT
        # Backend: every 3rd test, so 20 Zephyr + 13 qTest = 33 total
        assert backend.total_tests == 33
        assert backend.zephyr_tests == 20
        assert backend.qtest_tests == 13
        assert backend.adoption_ratio == pytest.approx(13 / 33, rel=0.01)

    def test_calculate_team_metrics_by_label(
        self, calculator, sample_zephyr_tests, sample_qtest_tests
    ):
        """Test team metrics calculation by label."""
        all_tests = sample_zephyr_tests + sample_qtest_tests

        team_metrics = calculator._calculate_team_metrics(
            all_tests, TeamSource.LABEL, sample_zephyr_tests, sample_qtest_tests
        )

        # Should have teams based on labels: team-0, team-1, team-2
        assert len(team_metrics) == 3
        assert "team-0" in team_metrics
        assert "team-1" in team_metrics
        assert "team-2" in team_metrics

    def test_update_tests_with_executions(self, calculator):
        """Test updating tests with execution data."""
        tests = [
            TestCaseModel(
                id="T-001",
                key="TC-001",
                summary="Test 1",
                project_key="TEST",
                source_system="zephyr",
                created=datetime.now(),
                updated=datetime.now(),
                status="Active",
            ),
            TestCaseModel(
                id="T-002",
                key="TC-002",
                summary="Test 2",
                project_key="TEST",
                source_system="zephyr",
                created=datetime.now(),
                updated=datetime.now(),
                status="Active",
            ),
        ]

        executions = {
            "T-001": {
                "last_execution": datetime.now().isoformat() + "Z",
                "status": "Passed",
                "linked_defects": [],
            },
            "T-002": {
                "last_execution": (datetime.now() - timedelta(days=1)).isoformat() + "Z",
                "status": "Failed",
                "linked_defects": ["BUG-123"],
            },
        }

        calculator._update_tests_with_executions(tests, executions)

        # Check updates
        assert tests[0].last_execution is not None
        assert tests[0].execution_status == "Passed"
        assert tests[1].last_execution is not None
        assert tests[1].execution_status == "Failed"

    def test_calculate_trend_data(self, calculator, mock_client):
        """Test 4-week trend calculation."""
        mock_now = datetime(2025, 1, 29, 12, 0, 0)

        # Mock different responses for different weeks
        def create_mock_test(source, assignee):
            mock_test = Mock()
            mock_test.source_system = source
            mock_test.assignee = assignee
            mock_test.last_execution = None
            mock_test.linked_defects = []
            return mock_test

        zephyr_responses = [
            [
                create_mock_test("zephyr", "user1@example.com") for _ in range(15)
            ],  # Week 1: 15 zephyr
            [
                create_mock_test("zephyr", "user1@example.com") for _ in range(12)
            ],  # Week 2: 12 zephyr
            [
                create_mock_test("zephyr", "user1@example.com") for _ in range(10)
            ],  # Week 3: 10 zephyr
            [create_mock_test("zephyr", "user1@example.com") for _ in range(8)],  # Week 4: 8 zephyr
        ]

        qtest_responses = [
            [create_mock_test("qtest", "user2@example.com") for _ in range(5)],  # Week 1: 5 qtest
            [create_mock_test("qtest", "user2@example.com") for _ in range(4)],  # Week 2: 4 qtest
            [create_mock_test("qtest", "user2@example.com") for _ in range(3)],  # Week 3: 3 qtest
            [create_mock_test("qtest", "user2@example.com") for _ in range(2)],  # Week 4: 2 qtest
        ]

        mock_client.get_zephyr_tests.side_effect = zephyr_responses
        mock_client.get_qtest_tests.side_effect = qtest_responses

        # Calculate trend
        trend = calculator._calculate_trend_data("TEST", TeamSource.COMPONENT, mock_now)

        # Verify trend data structure
        assert isinstance(trend, TrendData)

        # Week 1: 5/(5+15) = 0.25 adoption, 2 unique users
        assert trend.week_1["adoption_ratio"] == 0.25
        assert trend.week_1["active_users"] == 2

        # Week 4: 2/(2+8) = 0.2 adoption, 2 unique users
        assert trend.week_4["adoption_ratio"] == 0.2
        assert trend.week_4["active_users"] == 2

        # Trends (week 1 - week 4)
        assert abs(trend.adoption_trend - 0.05) < 0.01  # 0.25 - 0.20 (approximately)
        assert trend.activity_trend == 0  # 2 - 2

    def test_calculate_metrics_empty_project(self, calculator, mock_client, sample_project):
        """Test metrics calculation with no tests."""
        # Setup mocks with empty results
        mock_client.get_jira_project.return_value = sample_project
        mock_client.get_zephyr_tests.return_value = []
        mock_client.get_qtest_tests.return_value = []
        mock_client.get_test_executions.return_value = {}  # Empty dict for executions

        # Calculate metrics
        result = calculator.calculate_metrics("TEST", "30d")

        # Verify zero metrics
        assert result.total_tests == 0
        assert result.zephyr_tests == 0
        assert result.qtest_tests == 0
        assert result.adoption_ratio == 0.0
        assert result.coverage_parity == 0.0
        assert result.defect_link_rate == 0.0
        assert result.active_users == 0

    def test_calculate_metrics_all_zephyr(
        self, calculator, mock_client, sample_project, sample_zephyr_tests
    ):
        """Test metrics with only Zephyr tests (0% adoption)."""
        mock_client.get_jira_project.return_value = sample_project
        mock_client.get_zephyr_tests.return_value = sample_zephyr_tests
        mock_client.get_qtest_tests.return_value = []
        mock_client.get_test_executions.return_value = {}  # Empty dict for executions

        result = calculator.calculate_metrics("TEST", "30d")

        assert result.total_tests == 60
        assert result.zephyr_tests == 60
        assert result.qtest_tests == 0
        assert result.adoption_ratio == 0.0  # No qTest adoption

    def test_calculate_metrics_all_qtest(
        self, calculator, mock_client, sample_project, sample_qtest_tests
    ):
        """Test metrics with only qTest tests (100% adoption)."""
        mock_client.get_jira_project.return_value = sample_project
        mock_client.get_zephyr_tests.return_value = []
        mock_client.get_qtest_tests.return_value = sample_qtest_tests
        mock_client.get_test_executions.return_value = {}  # Empty dict for executions

        result = calculator.calculate_metrics("TEST", "30d")

        assert result.total_tests == 40
        assert result.zephyr_tests == 0
        assert result.qtest_tests == 40
        assert result.adoption_ratio == 1.0  # Full qTest adoption

    def test_calculate_metrics_with_executions(
        self, calculator, mock_client, sample_project, sample_zephyr_tests, sample_qtest_tests
    ):
        """Test metrics calculation with execution data."""
        # Setup mocks
        mock_client.get_jira_project.return_value = sample_project
        mock_client.get_zephyr_tests.return_value = sample_zephyr_tests
        mock_client.get_qtest_tests.return_value = sample_qtest_tests

        # Mock execution data as dict (API returns dict with test_id as key)
        executions = {}
        for test in sample_zephyr_tests[:30]:  # 50% executed
            executions[test.id] = {
                "last_execution": datetime.now().isoformat() + "Z",
                "status": "Passed",
                "linked_defects": [],
            }
        for test in sample_qtest_tests[:20]:  # 50% executed
            executions[test.id] = {
                "last_execution": datetime.now().isoformat() + "Z",
                "status": "Passed",
                "linked_defects": [],
            }

        mock_client.get_test_executions.return_value = executions

        # Calculate metrics
        result = calculator.calculate_metrics("TEST", "30d")

        # Verify execution tracking (called twice: once for zephyr, once for qtest)
        assert mock_client.get_test_executions.call_count == 2
        assert result.coverage_parity > 0  # Should have some coverage parity

    def test_time_window_formats(self, calculator, mock_client, sample_project):
        """Test various time window format support."""
        mock_client.get_jira_project.return_value = sample_project
        mock_client.get_zephyr_tests.return_value = []
        mock_client.get_qtest_tests.return_value = []
        mock_client.get_test_executions.return_value = {}  # Empty dict for executions

        # Test different formats (only d, w, and plain numbers are supported)
        for window in ["7d", "14d", "30d", "1w", "2w", "4w", "30", "90"]:
            result = calculator.calculate_metrics("TEST", window)
            assert result.time_window == window

        # Test invalid format (succeeds but uses default window)
        result = calculator.calculate_metrics("TEST", "invalid_window")
        assert result.time_window == "invalid_window"  # Window is stored as-is

    def test_team_source_options(
        self, calculator, mock_client, sample_project, sample_zephyr_tests, sample_qtest_tests
    ):
        """Test different team source options."""
        mock_client.get_jira_project.return_value = sample_project
        mock_client.get_zephyr_tests.return_value = sample_zephyr_tests
        mock_client.get_qtest_tests.return_value = sample_qtest_tests
        mock_client.get_test_executions.return_value = {}  # Empty dict for executions

        # Test with COMPONENT source
        result = calculator.calculate_metrics("TEST", "30d", TeamSource.COMPONENT)
        assert len(result.team_metrics) == 3  # Backend, Frontend, QA

        # Test with LABEL source
        result = calculator.calculate_metrics("TEST", "30d", TeamSource.LABEL)
        assert len(result.team_metrics) == 3  # team-0, team-1, team-2

        # Test with GROUP source (should handle even if no groups)
        result = calculator.calculate_metrics("TEST", "30d", TeamSource.GROUP)
        assert isinstance(result.team_metrics, dict)
