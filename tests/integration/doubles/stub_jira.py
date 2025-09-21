"""
Stub implementation for Jira API - fixed responses for happy paths.
"""

from typing import Any


class JiraStub:
    """Stub Jira API with fixed responses."""

    def __init__(self, preset: str = "happy_small"):
        self.preset = preset
        self.responses = self._load_preset(preset)
        self.call_count = 0

    def _load_preset(self, preset: str) -> dict[str, Any]:
        """Load preset responses."""
        if preset == "happy_small":
            return {
                "project": {
                    "id": "10001",
                    "key": "TEST",
                    "name": "Test Project",
                    "components": [{"id": "1", "name": "Backend"}, {"id": "2", "name": "Frontend"}],
                },
                "search_page_1": {
                    "startAt": 0,
                    "maxResults": 50,
                    "total": 75,
                    "issues": self._generate_issues(0, 50),
                },
                "search_page_2": {
                    "startAt": 50,
                    "maxResults": 50,
                    "total": 75,
                    "issues": self._generate_issues(50, 25),
                },
                "myself": {
                    "accountId": "test-user-123",
                    "emailAddress": "test@example.com",
                    "displayName": "Test User",
                    "active": True,
                },
            }
        elif preset == "empty":
            return {
                "project": {
                    "id": "10002",
                    "key": "EMPTY",
                    "name": "Empty Project",
                    "components": [],
                },
                "search_page_1": {"startAt": 0, "maxResults": 50, "total": 0, "issues": []},
            }
        else:
            raise ValueError(f"Unknown preset: {preset}")

    def _generate_issues(self, start: int, count: int) -> list[dict[str, Any]]:
        """Generate deterministic test issues."""
        issues = []
        for i in range(start + 1, start + count + 1):
            issues.append(
                {
                    "id": f"1000{i}",
                    "key": f"TEST-{i}",
                    "fields": {
                        "summary": f"Test issue {i}",
                        "status": {"name": "Done" if i % 3 == 0 else "Open"},
                        "assignee": (
                            {"emailAddress": f"user{i%3}@example.com"} if i % 2 == 0 else None
                        ),
                        "components": [{"name": "Backend" if i % 2 == 0 else "Frontend"}],
                        "labels": ["automated"] if i % 4 == 0 else [],
                    },
                }
            )
        return issues

    def get_project(self, project_key: str) -> dict[str, Any]:
        """Get project stub response."""
        self.call_count += 1
        return self.responses["project"]

    def search_issues(self, jql: str, start_at: int = 0, max_results: int = 50) -> dict[str, Any]:
        """Search issues stub response with pagination."""
        self.call_count += 1
        if start_at == 0:
            return self.responses.get("search_page_1")
        elif start_at == 50:
            return self.responses.get("search_page_2")
        else:
            return {"startAt": start_at, "maxResults": max_results, "total": 75, "issues": []}

    def get_myself(self) -> dict[str, Any]:
        """Get current user stub response."""
        self.call_count += 1
        return self.responses["myself"]
