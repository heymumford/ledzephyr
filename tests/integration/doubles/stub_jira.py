"""Jira API stub for integration testing."""

from datetime import datetime
from typing import Any


class JiraAPIStub:
    """Stub implementation of Jira API for testing."""

    def __init__(self, preset: str = "basic_project"):
        """Initialize with a preset configuration."""
        self.preset = preset
        self.call_log = []
        self._setup_preset_data()

    def _setup_preset_data(self):
        """Setup test data based on preset."""
        if self.preset == "basic_project":
            self.project_data = {
                "key": "DEMO",
                "name": "Demo Project",
                "description": "Demo project for testing",
                "lead": {"displayName": "Project Lead"},
                "components": [{"name": "Frontend"}, {"name": "Backend"}, {"name": "Database"}],
            }
            self.myself_data = {
                "name": "test.user",
                "displayName": "Test User",
                "emailAddress": "test@example.com",
            }

        elif self.preset == "large_project":
            self.project_data = {
                "key": "LARGE",
                "name": "Large Enterprise Project",
                "description": "Large project with many components",
                "lead": {"displayName": "Enterprise Lead"},
                "components": [{"name": f"Component-{i:02d}"} for i in range(1, 11)],
            }
            self.myself_data = {
                "name": "enterprise.user",
                "displayName": "Enterprise User",
                "emailAddress": "enterprise@bigcorp.com",
            }

        elif self.preset == "empty_project":
            self.project_data = {
                "key": "EMPTY",
                "name": "Empty Project",
                "description": "Project with no components",
                "lead": {"displayName": "Empty Lead"},
                "components": [],
            }
            self.myself_data = {
                "name": "empty.user",
                "displayName": "Empty User",
                "emailAddress": "empty@example.com",
            }

    def get_project(self, project_key: str) -> dict[str, Any]:
        """Stub for GET /rest/api/2/project/{projectKey}."""
        self.call_log.append(
            {
                "method": "GET",
                "url": f"/rest/api/2/project/{project_key}",
                "timestamp": datetime.now().isoformat(),
            }
        )

        if project_key == self.project_data["key"]:
            return self.project_data
        else:
            raise ValueError(f"Project {project_key} not found")

    def get_myself(self) -> dict[str, Any]:
        """Stub for GET /rest/api/2/myself."""
        self.call_log.append(
            {"method": "GET", "url": "/rest/api/2/myself", "timestamp": datetime.now().isoformat()}
        )
        return self.myself_data

    def get_call_log(self) -> list[dict[str, Any]]:
        """Get the log of all API calls made."""
        return self.call_log.copy()

    def clear_call_log(self):
        """Clear the call log."""
        self.call_log.clear()


class ZephyrAPIStub:
    """Stub implementation of Zephyr Scale API for testing."""

    def __init__(self, preset: str = "mixed_execution_status"):
        """Initialize with a preset configuration."""
        self.preset = preset
        self.call_log = []
        self._setup_preset_data()

    def _setup_preset_data(self):
        """Setup test data based on preset."""
        if self.preset == "mixed_execution_status":
            self.test_cases = {
                "values": [
                    {
                        "id": "Z-1",
                        "key": "Z-1",
                        "name": "User login test",
                        "component": "Frontend",
                        "labels": ["ui", "smoke"],
                        "owner": {"displayName": "alice@example.com"},
                        "createdOn": "2025-06-25T10:00:00Z",
                        "updatedOn": "2025-06-30T15:30:00Z",
                        "status": "Done",
                    },
                    {
                        "id": "Z-2",
                        "key": "Z-2",
                        "name": "API endpoint test",
                        "component": "Backend",
                        "labels": ["api", "integration"],
                        "owner": {"displayName": "bob@example.com"},
                        "createdOn": "2025-06-24T09:00:00Z",
                        "updatedOn": "2025-06-30T16:00:00Z",
                        "status": "Done",
                    },
                ]
            }
            self.test_runs = {
                "Z-1": {
                    "values": [
                        {"executedOn": "2025-06-30T14:00:00Z", "status": "PASS", "issues": []}
                    ]
                },
                "Z-2": {"values": []},  # No executions
            }

        elif self.preset == "all_executed":
            self.test_cases = {
                "values": [
                    {
                        "id": "Z-10",
                        "key": "Z-10",
                        "name": "Executed test 1",
                        "component": "Frontend",
                        "labels": ["executed"],
                        "owner": {"displayName": "tester@example.com"},
                        "createdOn": "2025-06-20T10:00:00Z",
                        "updatedOn": "2025-06-30T10:00:00Z",
                        "status": "Done",
                    }
                ]
            }
            self.test_runs = {
                "Z-10": {
                    "values": [
                        {
                            "executedOn": "2025-06-30T10:00:00Z",
                            "status": "PASS",
                            "issues": ["BUG-123"],
                        }
                    ]
                }
            }

    def search_test_cases(self, project_key: str, **params) -> dict[str, Any]:
        """Stub for GET /rest/atm/1.0/testcase/search."""
        self.call_log.append(
            {
                "method": "GET",
                "url": "/rest/atm/1.0/testcase/search",
                "params": {"projectKey": project_key, **params},
                "timestamp": datetime.now().isoformat(),
            }
        )
        return self.test_cases

    def search_test_runs(self, test_case_key: str, **params) -> dict[str, Any]:
        """Stub for GET /rest/atm/1.0/testrun/search."""
        self.call_log.append(
            {
                "method": "GET",
                "url": "/rest/atm/1.0/testrun/search",
                "params": {"testCaseKey": test_case_key, **params},
                "timestamp": datetime.now().isoformat(),
            }
        )
        return self.test_runs.get(test_case_key, {"values": []})

    def health_check(self) -> dict[str, Any]:
        """Stub for GET /rest/atm/1.0/healthcheck."""
        self.call_log.append(
            {
                "method": "GET",
                "url": "/rest/atm/1.0/healthcheck",
                "timestamp": datetime.now().isoformat(),
            }
        )
        return {"status": "UP"}

    def get_call_log(self) -> list[dict[str, Any]]:
        """Get the log of all API calls made."""
        return self.call_log.copy()

    def clear_call_log(self):
        """Clear the call log."""
        self.call_log.clear()


class QTestAPIStub:
    """Stub implementation of qTest API for testing."""

    def __init__(self, preset: str = "basic_tests"):
        """Initialize with a preset configuration."""
        self.preset = preset
        self.call_log = []
        self._setup_preset_data()

    def _setup_preset_data(self):
        """Setup test data based on preset."""
        if self.preset == "basic_tests":
            self.projects = [{"id": 12345, "name": "DEMO"}, {"id": 67890, "name": "OTHER"}]
            self.test_cases = {
                12345: {  # DEMO project
                    "items": [
                        {
                            "id": 1001,
                            "name": "User registration flow",
                            "created_date": "2025-06-26T11:00:00Z",
                            "last_modified_date": "2025-06-30T17:00:00Z",
                            "status": "Active",
                            "tags": ["ui", "regression"],
                        },
                        {
                            "id": 1002,
                            "name": "Payment processing",
                            "created_date": "2025-06-23T08:00:00Z",
                            "last_modified_date": "2025-06-30T18:00:00Z",
                            "status": "Active",
                            "tags": ["payment", "critical"],
                        },
                    ]
                }
            }

    def get_projects(self) -> list[dict[str, Any]]:
        """Stub for GET /api/v3/projects."""
        self.call_log.append(
            {"method": "GET", "url": "/api/v3/projects", "timestamp": datetime.now().isoformat()}
        )
        return self.projects

    def get_test_cases(self, project_id: int, **params) -> dict[str, Any]:
        """Stub for GET /api/v3/projects/{projectId}/test-cases."""
        self.call_log.append(
            {
                "method": "GET",
                "url": f"/api/v3/projects/{project_id}/test-cases",
                "params": params,
                "timestamp": datetime.now().isoformat(),
            }
        )
        return self.test_cases.get(project_id, {"items": []})

    def get_user(self) -> dict[str, Any]:
        """Stub for GET /api/v3/users/me."""
        self.call_log.append(
            {"method": "GET", "url": "/api/v3/users/me", "timestamp": datetime.now().isoformat()}
        )
        return {"id": 999, "username": "test.user", "email": "test@example.com"}

    def get_call_log(self) -> list[dict[str, Any]]:
        """Get the log of all API calls made."""
        return self.call_log.copy()

    def clear_call_log(self):
        """Clear the call log."""
        self.call_log.clear()
