"""
Stub implementation for qTest API - fixed responses for happy paths.
"""

from datetime import UTC, datetime
from typing import Any


class QTestStub:
    """Stub qTest API with fixed responses."""

    def __init__(self, preset: str = "happy_small"):
        self.preset = preset
        self.responses = self._load_preset(preset)
        self.call_count = 0

    def _load_preset(self, preset: str) -> dict[str, Any]:
        """Load preset responses."""
        if preset == "happy_small":
            return {
                "projects": [
                    {
                        "id": 12345,
                        "name": "Test Project Alpha",
                        "description": "Main testing project",
                        "status": "Active",
                    },
                    {
                        "id": 12346,
                        "name": "Test Project Beta",
                        "description": "Secondary project",
                        "status": "Active",
                    },
                ],
                "test_cases_page_1": {
                    "page": 1,
                    "pageSize": 100,
                    "total": 150,
                    "items": self._generate_test_cases(0, 100),
                },
                "test_cases_page_2": {
                    "page": 2,
                    "pageSize": 100,
                    "total": 150,
                    "items": self._generate_test_cases(100, 50),
                },
                "test_runs": {
                    "page": 1,
                    "pageSize": 100,
                    "total": 75,
                    "items": self._generate_test_runs(75),
                },
                "test_cycles": {
                    "page": 1,
                    "pageSize": 100,
                    "total": 10,
                    "items": self._generate_test_cycles(10),
                },
                "test_suites": {
                    "page": 1,
                    "pageSize": 100,
                    "total": 8,
                    "items": self._generate_test_suites(8),
                },
            }
        elif preset == "empty":
            return {
                "projects": [
                    {
                        "id": 12347,
                        "name": "Empty Project",
                        "description": "No test data",
                        "status": "Active",
                    }
                ],
                "test_cases_page_1": {"page": 1, "pageSize": 100, "total": 0, "items": []},
                "test_runs": {"page": 1, "pageSize": 100, "total": 0, "items": []},
                "test_cycles": {"page": 1, "pageSize": 100, "total": 0, "items": []},
            }
        else:
            raise ValueError(f"Unknown preset: {preset}")

    def _generate_test_cases(self, start: int, count: int) -> list[dict[str, Any]]:
        """Generate deterministic test cases."""
        test_cases = []
        for i in range(start + 1, start + count + 1):
            test_cases.append(
                {
                    "id": 100000 + i,
                    "name": f"Test Case {i}",
                    "description": f"Description for test case {i}",
                    "test_case_version_id": 200000 + i,
                    "project_id": 12345,
                    "created_date": "2024-01-01T00:00:00Z",
                    "last_modified_date": "2024-01-02T00:00:00Z",
                    "properties": [
                        {"field_id": 1, "field_value": "Automated" if i % 3 == 0 else "Manual"},
                        {"field_id": 2, "field_value": "High" if i % 4 == 0 else "Medium"},
                        {
                            "field_id": 3,
                            "field_value": "Regression" if i % 5 == 0 else "Functional",
                        },
                    ],
                    "test_steps": self._generate_test_steps(i % 5 + 1),
                }
            )
        return test_cases

    def _generate_test_steps(self, count: int) -> list[dict[str, Any]]:
        """Generate test steps for a test case."""
        steps = []
        for i in range(1, count + 1):
            steps.append(
                {
                    "order": i,
                    "description": f"Step {i} description",
                    "expected_result": f"Expected result for step {i}",
                }
            )
        return steps

    def _generate_test_runs(self, count: int) -> list[dict[str, Any]]:
        """Generate deterministic test runs."""
        test_runs = []
        statuses = ["PASSED", "FAILED", "BLOCKED", "INCOMPLETE"]
        for i in range(1, count + 1):
            test_runs.append(
                {
                    "id": 300000 + i,
                    "name": f"Test Run {i}",
                    "test_case": {
                        "id": 100000 + (i % 150) + 1,
                        "name": f"Test Case {(i % 150) + 1}",
                    },
                    "test_cycle": {
                        "id": 400000 + (i % 10) + 1,
                        "name": f"Test Cycle {(i % 10) + 1}",
                    },
                    "status": {"name": statuses[i % 4]},
                    "exe_start_date": f"2024-01-{(i % 28) + 1:02d}T08:00:00Z",
                    "exe_end_date": f"2024-01-{(i % 28) + 1:02d}T09:00:00Z",
                    "assigned_to": f"user{i % 5}@example.com",
                }
            )
        return test_runs

    def _generate_test_cycles(self, count: int) -> list[dict[str, Any]]:
        """Generate deterministic test cycles."""
        cycles = []
        for i in range(1, count + 1):
            cycles.append(
                {
                    "id": 400000 + i,
                    "name": f"Test Cycle {i}",
                    "description": f"Test cycle {i} for Sprint {i}",
                    "pid": f"CY-{i:04d}",
                    "created_date": f"2024-01-{i:02d}T00:00:00Z",
                    "last_modified_date": f"2024-01-{i+1:02d}T00:00:00Z",
                    "target_release_id": 500000 + i,
                    "target_build_id": 600000 + i,
                    "is_active": i > 7,  # Last 3 cycles are active
                    "properties": [{"field_id": 10, "field_value": f"Sprint {i}"}],
                }
            )
        return cycles

    def _generate_test_suites(self, count: int) -> list[dict[str, Any]]:
        """Generate deterministic test suites."""
        suites = []
        for i in range(1, count + 1):
            suites.append(
                {
                    "id": 700000 + i,
                    "name": f"Test Suite {i}",
                    "parent_id": 700000 if i > 4 else None,  # Nested suites
                    "created_date": "2024-01-01T00:00:00Z",
                    "last_modified_date": "2024-01-02T00:00:00Z",
                }
            )
        return suites

    def get_projects(self) -> list[dict[str, Any]]:
        """Get projects stub response."""
        self.call_count += 1
        return self.responses["projects"]

    def get_test_cases(self, project_id: int, page: int = 1, size: int = 100) -> dict[str, Any]:
        """Get test cases stub response with pagination."""
        self.call_count += 1
        if page == 1:
            return self.responses.get("test_cases_page_1")
        elif page == 2:
            return self.responses.get("test_cases_page_2")
        else:
            return {"page": page, "pageSize": size, "total": 150, "items": []}

    def get_test_runs(self, project_id: int, page: int = 1, size: int = 100) -> dict[str, Any]:
        """Get test runs stub response."""
        self.call_count += 1
        return self.responses.get("test_runs")

    def get_test_cycles(self, project_id: int, page: int = 1, size: int = 100) -> dict[str, Any]:
        """Get test cycles stub response."""
        self.call_count += 1
        return self.responses.get("test_cycles")

    def get_test_suites(self, project_id: int, page: int = 1, size: int = 100) -> dict[str, Any]:
        """Get test suites stub response."""
        self.call_count += 1
        return self.responses.get(
            "test_suites", {"page": 1, "pageSize": 100, "total": 0, "items": []}
        )

    def create_test_case(self, project_id: int, test_case_data: dict[str, Any]) -> dict[str, Any]:
        """Create test case stub response."""
        self.call_count += 1
        return {
            "id": 199999,
            "name": test_case_data.get("name", "New Test Case"),
            "description": test_case_data.get("description", ""),
            "test_case_version_id": 299999,
            "project_id": project_id,
            "created_date": datetime.now(UTC).isoformat(),
            "last_modified_date": datetime.now(UTC).isoformat(),
        }

    def update_test_run(self, project_id: int, run_id: int, status: str) -> dict[str, Any]:
        """Update test run stub response."""
        self.call_count += 1
        return {
            "id": run_id,
            "status": {"name": status},
            "last_modified_date": datetime.now(UTC).isoformat(),
        }
