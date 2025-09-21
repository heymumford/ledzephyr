"""
Stub implementation for Zephyr Scale API - fixed responses for happy paths.
"""

from datetime import UTC, datetime
from typing import Any


class ZephyrStub:
    """Stub Zephyr Scale API with fixed responses."""

    def __init__(self, preset: str = "happy_small"):
        self.preset = preset
        self.responses = self._load_preset(preset)
        self.call_count = 0

    def _load_preset(self, preset: str) -> dict[str, Any]:
        """Load preset responses."""
        if preset == "happy_small":
            return {
                "testcases_page_1": {
                    "startAt": 0,
                    "maxResults": 50,
                    "total": 45,
                    "values": self._generate_testcases(0, 45),
                },
                "testcycles": {
                    "startAt": 0,
                    "maxResults": 50,
                    "total": 5,
                    "values": self._generate_testcycles(5),
                },
                "testexecutions": {
                    "startAt": 0,
                    "maxResults": 50,
                    "total": 120,
                    "values": self._generate_testexecutions(50),
                },
            }
        elif preset == "empty":
            return {
                "testcases_page_1": {"startAt": 0, "maxResults": 50, "total": 0, "values": []},
                "testcycles": {"startAt": 0, "maxResults": 50, "total": 0, "values": []},
                "testexecutions": {"startAt": 0, "maxResults": 50, "total": 0, "values": []},
            }
        else:
            raise ValueError(f"Unknown preset: {preset}")

    def _generate_testcases(self, start: int, count: int) -> list[dict[str, Any]]:
        """Generate deterministic test cases."""
        testcases = []
        for i in range(start + 1, start + count + 1):
            testcases.append(
                {
                    "id": f"Z-TC-{i:04d}",
                    "key": f"Z-TC-{i:04d}",
                    "name": f"Test Case {i}",
                    "projectId": 10001,
                    "status": "Approved" if i % 3 == 0 else "Draft",
                    "labels": ["regression"] if i % 5 == 0 else [],
                    "priority": "High" if i % 4 == 0 else "Medium",
                    "component": "Backend" if i % 2 == 0 else "Frontend",
                    "estimatedTime": 300000 + (i * 1000),  # milliseconds
                    "createdOn": "2024-01-01T00:00:00Z",
                    "updatedOn": "2024-01-02T00:00:00Z",
                }
            )
        return testcases

    def _generate_testcycles(self, count: int) -> list[dict[str, Any]]:
        """Generate deterministic test cycles."""
        cycles = []
        for i in range(1, count + 1):
            cycles.append(
                {
                    "id": f"Z-CY-{i:04d}",
                    "key": f"Z-CY-{i:04d}",
                    "name": f"Test Cycle {i}",
                    "projectId": 10001,
                    "status": "Done" if i <= 2 else "In Progress",
                    "plannedStartDate": f"2024-01-{i:02d}T00:00:00Z",
                    "plannedEndDate": f"2024-01-{i+7:02d}T00:00:00Z",
                    "iteration": f"Sprint {i}",
                }
            )
        return cycles

    def _generate_testexecutions(self, count: int) -> list[dict[str, Any]]:
        """Generate deterministic test executions."""
        executions = []
        statuses = ["Pass", "Fail", "Blocked", "Not Executed"]
        for i in range(1, count + 1):
            executions.append(
                {
                    "id": f"Z-EX-{i:05d}",
                    "testCaseId": f"Z-TC-{(i % 45) + 1:04d}",
                    "testCycleId": f"Z-CY-{(i % 5) + 1:04d}",
                    "status": statuses[i % 4],
                    "executionTime": 180000 + (i * 500),  # milliseconds
                    "executedOn": f"2024-01-{(i % 28) + 1:02d}T{(i % 24):02d}:00:00Z",
                    "executedBy": f"user{i % 3}@example.com",
                    "comment": f"Execution comment {i}" if i % 3 == 0 else None,
                }
            )
        return executions

    def get_testcases(
        self, project_id: int, start_at: int = 0, max_results: int = 50
    ) -> dict[str, Any]:
        """Get test cases stub response."""
        self.call_count += 1
        return self.responses.get("testcases_page_1")

    def get_testcycles(
        self, project_id: int, start_at: int = 0, max_results: int = 50
    ) -> dict[str, Any]:
        """Get test cycles stub response."""
        self.call_count += 1
        return self.responses.get("testcycles")

    def get_testexecutions(
        self, project_id: int, start_at: int = 0, max_results: int = 50
    ) -> dict[str, Any]:
        """Get test executions stub response."""
        self.call_count += 1
        if start_at == 0:
            response = self.responses.get("testexecutions").copy()
            response["values"] = response["values"][:max_results]
            return response
        elif start_at == 50:
            response = self.responses.get("testexecutions").copy()
            response["startAt"] = 50
            response["values"] = response["values"][50:100] if len(response["values"]) > 50 else []
            return response
        else:
            return {"startAt": start_at, "maxResults": max_results, "total": 120, "values": []}

    def create_testcase(self, project_id: int, testcase_data: dict[str, Any]) -> dict[str, Any]:
        """Create test case stub response."""
        self.call_count += 1
        return {
            "id": "Z-TC-9999",
            "key": "Z-TC-9999",
            "name": testcase_data.get("name", "New Test Case"),
            "projectId": project_id,
            "status": "Draft",
            "createdOn": datetime.now(UTC).isoformat(),
        }
