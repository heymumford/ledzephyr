"""
Fake implementation for Jira API - in-memory with state and error toggles.
"""

import time
from datetime import UTC, datetime
from typing import Any


class JiraFake:
    """Fake Jira API with in-memory state, pagination, and error simulation."""

    def __init__(self):
        # In-memory data store
        self.projects = {}
        self.issues = {}
        self.users = {}

        # Error simulation toggles
        self.rate_limit_enabled = False
        self.rate_limit_count = 0
        self.rate_limit_threshold = 10
        self.server_error_enabled = False
        self.network_timeout_enabled = False
        self.auth_error_enabled = False

        # Request tracking
        self.request_history = []
        self.call_count = 0

        # Initialize with default data
        self._initialize_default_data()

    def _initialize_default_data(self):
        """Initialize with some default data."""
        # Default project
        self.projects["TEST"] = {
            "id": "10001",
            "key": "TEST",
            "name": "Test Project",
            "components": [{"id": "1", "name": "Backend"}, {"id": "2", "name": "Frontend"}],
            "versions": [],
            "issueTypes": [
                {"id": "1", "name": "Bug"},
                {"id": "2", "name": "Story"},
                {"id": "3", "name": "Task"},
            ],
        }

        # Default user
        self.users["test-user-123"] = {
            "accountId": "test-user-123",
            "emailAddress": "test@example.com",
            "displayName": "Test User",
            "active": True,
        }

        # Generate some default issues
        for i in range(1, 101):
            issue_key = f"TEST-{i}"
            self.issues[issue_key] = {
                "id": f"1000{i}",
                "key": issue_key,
                "fields": {
                    "summary": f"Test issue {i}",
                    "description": f"Description for issue {i}",
                    "status": {
                        "name": "Done" if i % 3 == 0 else "In Progress" if i % 2 == 0 else "Open"
                    },
                    "assignee": (
                        {"accountId": "test-user-123", "emailAddress": "test@example.com"}
                        if i % 2 == 0
                        else None
                    ),
                    "reporter": {"accountId": "test-user-123", "emailAddress": "test@example.com"},
                    "priority": {"name": "High" if i % 4 == 0 else "Medium"},
                    "issuetype": {"name": "Bug" if i % 3 == 0 else "Story"},
                    "components": [{"name": "Backend" if i % 2 == 0 else "Frontend"}],
                    "labels": ["automated"] if i % 4 == 0 else [],
                    "created": f"2024-01-{(i % 28) + 1:02d}T00:00:00Z",
                    "updated": f"2024-01-{(i % 28) + 2:02d}T00:00:00Z",
                },
            }

    def _check_errors(self):
        """Check and raise errors based on toggles."""
        if self.auth_error_enabled:
            raise Exception("401 Unauthorized: Invalid authentication credentials")

        if self.server_error_enabled:
            raise Exception("500 Internal Server Error")

        if self.network_timeout_enabled:
            time.sleep(30)  # Simulate timeout
            raise Exception("Network timeout")

        if self.rate_limit_enabled:
            self.rate_limit_count += 1
            if self.rate_limit_count > self.rate_limit_threshold:
                raise Exception("429 Too Many Requests: Rate limit exceeded")

    def _track_request(self, method: str, endpoint: str, params: dict | None = None):
        """Track API request for spy functionality."""
        self.call_count += 1
        self.request_history.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "method": method,
                "endpoint": endpoint,
                "params": params or {},
                "call_number": self.call_count,
            }
        )

    def reset_errors(self):
        """Reset all error toggles."""
        self.rate_limit_enabled = False
        self.rate_limit_count = 0
        self.server_error_enabled = False
        self.network_timeout_enabled = False
        self.auth_error_enabled = False

    def enable_rate_limit(self, threshold: int = 10):
        """Enable rate limiting after threshold requests."""
        self.rate_limit_enabled = True
        self.rate_limit_threshold = threshold
        self.rate_limit_count = 0

    def get_project(self, project_key: str) -> dict[str, Any]:
        """Get project with error simulation."""
        self._track_request("GET", f"/project/{project_key}")
        self._check_errors()

        if project_key not in self.projects:
            raise Exception(f"404 Not Found: Project {project_key} not found")

        return self.projects[project_key]

    def search_issues(self, jql: str, start_at: int = 0, max_results: int = 50) -> dict[str, Any]:
        """Search issues with real pagination and JQL parsing."""
        self._track_request(
            "GET", "/search", {"jql": jql, "startAt": start_at, "maxResults": max_results}
        )
        self._check_errors()

        # Simple JQL parsing (just for project key)
        matching_issues = []
        if "project =" in jql:
            project_key = jql.split("project = ")[1].split(" ")[0].strip()
            matching_issues = [
                issue
                for issue in self.issues.values()
                if issue["key"].startswith(f"{project_key}-")
            ]
        else:
            matching_issues = list(self.issues.values())

        # Apply status filter if present
        if "status =" in jql:
            status = jql.split("status = ")[1].split(" ")[0].strip().strip("'\"")
            matching_issues = [
                issue
                for issue in matching_issues
                if issue["fields"]["status"]["name"].lower() == status.lower()
            ]

        # Apply assignee filter if present
        if "assignee =" in jql:
            assignee = jql.split("assignee = ")[1].split(" ")[0].strip()
            if assignee == "currentUser()":
                matching_issues = [
                    issue
                    for issue in matching_issues
                    if issue["fields"]["assignee"]
                    and issue["fields"]["assignee"]["accountId"] == "test-user-123"
                ]

        # Paginate results
        total = len(matching_issues)
        paginated = matching_issues[start_at : start_at + max_results]

        return {"startAt": start_at, "maxResults": max_results, "total": total, "issues": paginated}

    def get_issue(self, issue_key: str) -> dict[str, Any]:
        """Get single issue."""
        self._track_request("GET", f"/issue/{issue_key}")
        self._check_errors()

        if issue_key not in self.issues:
            raise Exception(f"404 Not Found: Issue {issue_key} not found")

        return self.issues[issue_key]

    def create_issue(self, issue_data: dict[str, Any]) -> dict[str, Any]:
        """Create new issue."""
        self._track_request("POST", "/issue", issue_data)
        self._check_errors()

        # Generate new issue key
        project_key = issue_data["fields"].get("project", {}).get("key", "TEST")
        issue_num = len([k for k in self.issues.keys() if k.startswith(f"{project_key}-")]) + 1
        issue_key = f"{project_key}-{issue_num}"

        new_issue = {
            "id": f"1000{issue_num}",
            "key": issue_key,
            "fields": {
                "summary": issue_data["fields"].get("summary", "New Issue"),
                "description": issue_data["fields"].get("description", ""),
                "status": {"name": "Open"},
                "assignee": issue_data["fields"].get("assignee"),
                "reporter": {"accountId": "test-user-123", "emailAddress": "test@example.com"},
                "priority": issue_data["fields"].get("priority", {"name": "Medium"}),
                "issuetype": issue_data["fields"].get("issuetype", {"name": "Task"}),
                "components": issue_data["fields"].get("components", []),
                "labels": issue_data["fields"].get("labels", []),
                "created": datetime.now(UTC).isoformat(),
                "updated": datetime.now(UTC).isoformat(),
            },
        }

        self.issues[issue_key] = new_issue
        return new_issue

    def update_issue(self, issue_key: str, update_data: dict[str, Any]) -> dict[str, Any]:
        """Update existing issue."""
        self._track_request("PUT", f"/issue/{issue_key}", update_data)
        self._check_errors()

        if issue_key not in self.issues:
            raise Exception(f"404 Not Found: Issue {issue_key} not found")

        # Update fields
        issue = self.issues[issue_key]
        if "fields" in update_data:
            issue["fields"].update(update_data["fields"])
        issue["fields"]["updated"] = datetime.now(UTC).isoformat()

        return issue

    def get_myself(self) -> dict[str, Any]:
        """Get current user."""
        self._track_request("GET", "/myself")
        self._check_errors()

        return self.users["test-user-123"]

    def get_request_history(self) -> list[dict[str, Any]]:
        """Get request history for spy functionality."""
        return self.request_history

    def clear_data(self):
        """Clear all in-memory data."""
        self.projects.clear()
        self.issues.clear()
        self.users.clear()
        self.request_history.clear()
        self.call_count = 0
        self._initialize_default_data()
