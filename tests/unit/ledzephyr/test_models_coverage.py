"""Simple unit tests for models to improve coverage."""

import pytest

from ledzephyr.models import APIConnectionStatus, JiraProject, ProjectMetrics, TestCaseModel


@pytest.mark.unit
class TestModels:
    """Test data models."""

    def test_jira_project_creation(self):
        """Test JiraProject model creation."""
        project = JiraProject(
            key="TEST",
            name="Test Project",
            description="A test project",
            components=["Backend", "Frontend"],
            issue_types=["Bug", "Task"],
        )
        assert project.key == "TEST"
        assert project.name == "Test Project"
        assert "Backend" in project.components
        assert len(project.issue_types) == 2

    def test_test_case_model_creation(self):
        """Test TestCaseModel creation."""
        test_case = TestCaseModel(
            key="TC-001",
            summary="Test login functionality",
            description="Verify user can log in",
            component="Frontend",
            status="Active",
            priority="High",
            test_type="Manual",
        )
        assert test_case.key == "TC-001"
        assert test_case.summary == "Test login functionality"
        assert test_case.component == "Frontend"
        assert test_case.status == "Active"

    def test_api_connection_status_creation(self):
        """Test APIConnectionStatus model creation."""
        status = APIConnectionStatus(
            service="Jira", connected=True, message="Successfully connected", error=None
        )
        assert status.service == "Jira"
        assert status.connected is True
        assert status.message == "Successfully connected"
        assert status.error is None

    def test_project_metrics_creation(self):
        """Test ProjectMetrics model creation."""
        from datetime import datetime

        metrics = ProjectMetrics(
            project_key="TEST",
            total_tests=100,
            passed_tests=80,
            failed_tests=10,
            blocked_tests=5,
            unexecuted_tests=5,
            pass_rate=80.0,
            defect_density=0.1,
            execution_time=datetime(2025, 1, 1, 12, 0, 0),
            last_execution=datetime(2025, 1, 1, 12, 0, 0),
            components=["Backend", "Frontend"],
            test_cycle="Sprint 1",
            environment="Test",
        )
        assert metrics.project_key == "TEST"
        assert metrics.total_tests == 100
        assert metrics.passed_tests == 80
        assert metrics.pass_rate == 80.0
        assert "Backend" in metrics.components
