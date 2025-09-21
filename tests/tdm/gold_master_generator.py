#!/usr/bin/env python3
"""
Gold Master Test Data Generator for LedZephyr.

Generates realistic, deterministic test data that matches actual vendor API responses
and supports all metrics calculations.
"""

import hashlib
import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any


class TestStatus(str, Enum):
    """Test execution status."""

    PASSED = "Pass"
    FAILED = "Fail"
    BLOCKED = "Blocked"
    NOT_EXECUTED = "Not Executed"
    IN_PROGRESS = "In Progress"


class MigrationScenario(str, Enum):
    """Migration scenarios for testing."""

    FRESH = "fresh"  # 100% Zephyr
    IN_PROGRESS = "in_progress"  # 60% Zephyr, 40% qTest
    COMPLETE = "complete"  # 100% qTest
    TEAM_BASED = "team_based"  # Different adoption per team
    EDGE_CASES = "edge_cases"  # Various edge conditions


@dataclass
class GoldMasterConfig:
    """Configuration for gold master data generation."""

    scenario: MigrationScenario
    project_key: str
    num_teams: int = 4
    total_tests: int = 500
    time_range_days: int = 90
    defect_link_rate: float = 0.20  # 20% of tests have defects
    execution_rate: float = 0.85  # 85% of tests have been executed
    pass_rate: float = 0.70  # 70% of executed tests pass
    seed: int = 42  # For deterministic generation


class GoldMasterGenerator:
    """Generate gold master test data for all vendors."""

    def __init__(self, config: GoldMasterConfig):
        self.config = config
        random.seed(config.seed)
        self.teams = self._generate_teams()
        self.users = self._generate_users()
        self.defects = self._generate_defects()

    def _generate_teams(self) -> list[dict[str, Any]]:
        """Generate team data."""
        teams = []
        team_names = ["Platform", "Frontend", "Backend", "Mobile", "QA", "DevOps"]

        for i in range(self.config.num_teams):
            teams.append(
                {
                    "name": team_names[i % len(team_names)],
                    "component": f"Component-{team_names[i % len(team_names)]}",
                    "label": f"team-{team_names[i % len(team_names)].lower()}",
                    "adoption_rate": self._get_team_adoption_rate(i),
                }
            )

        return teams

    def _get_team_adoption_rate(self, team_index: int) -> float:
        """Get adoption rate based on scenario."""
        if self.config.scenario == MigrationScenario.FRESH:
            return 0.0
        elif self.config.scenario == MigrationScenario.COMPLETE:
            return 1.0
        elif self.config.scenario == MigrationScenario.IN_PROGRESS:
            return 0.4  # 40% overall
        elif self.config.scenario == MigrationScenario.TEAM_BASED:
            # Different rates per team
            rates = [0.8, 0.6, 0.2, 0.1]
            return rates[team_index % len(rates)]
        else:  # EDGE_CASES
            return random.random()

    def _generate_users(self) -> list[dict[str, Any]]:
        """Generate user data."""
        users = []
        for i in range(10):  # 10 users
            users.append(
                {
                    "id": f"user-{i:03d}",
                    "email": f"user{i}@example.com",
                    "display_name": f"Test User {i}",
                    "active": i < 8,  # 8 active, 2 inactive
                }
            )
        return users

    def _generate_defects(self) -> list[str]:
        """Generate defect IDs."""
        return [f"BUG-{i:04d}" for i in range(1, 101)]  # 100 defects

    def generate_jira_project(self) -> dict[str, Any]:
        """Generate Jira project data."""
        return {
            "key": self.config.project_key,
            "name": f"Test Project {self.config.project_key}",
            "description": f"Gold master test project for {self.config.scenario.value} scenario",
            "lead": self.users[0]["email"],
            "components": [
                {"id": str(i), "name": team["component"]} for i, team in enumerate(self.teams)
            ],
            "issueTypes": [
                {"id": "1", "name": "Bug"},
                {"id": "2", "name": "Story"},
                {"id": "3", "name": "Task"},
                {"id": "4", "name": "Test"},
            ],
        }

    def generate_zephyr_tests(self) -> list[dict[str, Any]]:
        """Generate Zephyr Scale test cases."""
        tests = []

        # Calculate how many Zephyr tests based on scenario
        if self.config.scenario == MigrationScenario.FRESH:
            num_zephyr = self.config.total_tests
        elif self.config.scenario == MigrationScenario.COMPLETE:
            num_zephyr = 0
        elif self.config.scenario == MigrationScenario.IN_PROGRESS:
            num_zephyr = int(self.config.total_tests * 0.6)  # 60% Zephyr
        else:
            num_zephyr = self.config.total_tests // 2

        base_date = datetime.now() - timedelta(days=self.config.time_range_days)

        for i in range(num_zephyr):
            team = self.teams[i % len(self.teams)]
            user = self.users[i % len(self.users)]

            # Determine if this test should be in qTest (for team-based scenario)
            if self.config.scenario == MigrationScenario.TEAM_BASED:
                if random.random() < team["adoption_rate"]:
                    continue  # Skip this one, it'll be in qTest

            created = base_date + timedelta(
                days=random.randint(0, self.config.time_range_days - 10)
            )
            updated = created + timedelta(days=random.randint(0, 10))

            test = {
                "id": f"Z-TC-{i:05d}",
                "key": f"Z-TC-{i:05d}",
                "name": f"Test Case {i}: {self._generate_test_name(i)}",
                "projectKey": self.config.project_key,
                "folder": f"/Tests/{team['name']}",
                "status": random.choice(["Draft", "Approved", "Deprecated"]),
                "priority": random.choice(["High", "Medium", "Low"]),
                "component": team["component"],
                "labels": [team["label"], "automated" if i % 3 == 0 else "manual"],
                "owner": user["email"],
                "estimatedTime": random.randint(300000, 1800000),  # 5-30 minutes in ms
                "createdOn": created.isoformat() + "Z",
                "modifiedOn": updated.isoformat() + "Z",
                "customFields": {
                    "testType": random.choice(["Functional", "Regression", "Smoke", "Integration"]),
                    "automationStatus": "Automated" if i % 3 == 0 else "Manual",
                },
            }

            # Add test steps
            test["testSteps"] = [
                {
                    "index": j,
                    "description": f"Step {j}: {self._generate_step_description(j)}",
                    "expectedResult": f"Expected result {j}",
                    "testData": f"Test data {j}" if j % 2 == 0 else None,
                }
                for j in range(1, random.randint(3, 8))
            ]

            tests.append(test)

        return tests

    def generate_qtest_tests(self) -> list[dict[str, Any]]:
        """Generate qTest test cases."""
        tests = []

        # Calculate how many qTest tests based on scenario
        if self.config.scenario == MigrationScenario.FRESH:
            num_qtest = 0
        elif self.config.scenario == MigrationScenario.COMPLETE:
            num_qtest = self.config.total_tests
        elif self.config.scenario == MigrationScenario.IN_PROGRESS:
            num_qtest = int(self.config.total_tests * 0.4)  # 40% qTest
        else:
            num_qtest = self.config.total_tests - len(self.generate_zephyr_tests())

        base_date = datetime.now() - timedelta(days=self.config.time_range_days)

        for i in range(num_qtest):
            team = self.teams[i % len(self.teams)]
            user = self.users[i % len(self.users)]

            created = base_date + timedelta(
                days=random.randint(0, self.config.time_range_days - 10)
            )
            updated = created + timedelta(days=random.randint(0, 10))

            test = {
                "id": 100000 + i,
                "name": f"Test Case {i}: {self._generate_test_name(i + 1000)}",
                "description": f"qTest test case for {team['name']} team",
                "test_case_version_id": 200000 + i,
                "project_id": self._hash_project_key_to_id(),
                "parent_id": 300000 + (i // 10),  # Group tests in suites
                "created_date": created.isoformat() + "Z",
                "last_modified_date": updated.isoformat() + "Z",
                "properties": [
                    {"field_id": 1, "field_name": "Component", "field_value": team["component"]},
                    {
                        "field_id": 2,
                        "field_name": "Priority",
                        "field_value": random.choice(["High", "Medium", "Low"]),
                    },
                    {
                        "field_id": 3,
                        "field_name": "Type",
                        "field_value": random.choice(["Functional", "Regression", "Smoke"]),
                    },
                    {
                        "field_id": 4,
                        "field_name": "Automation",
                        "field_value": "Yes" if i % 3 == 0 else "No",
                    },
                    {"field_id": 5, "field_name": "Team", "field_value": team["label"]},
                ],
                "assigned_to_id": user["id"],
                "assigned_to": user["email"],
                "test_steps": [
                    {
                        "id": 400000 + (i * 10) + j,
                        "order": j,
                        "description": f"Step {j}: {self._generate_step_description(j)}",
                        "expected_result": f"Expected result {j}",
                    }
                    for j in range(1, random.randint(3, 8))
                ],
            }

            tests.append(test)

        return tests

    def generate_test_executions(self, source: str) -> list[dict[str, Any]]:
        """Generate test execution data."""
        executions = []

        if source == "zephyr":
            tests = self.generate_zephyr_tests()
            prefix = "Z-EX"
        else:
            tests = self.generate_qtest_tests()
            prefix = "Q-RUN"

        for test in tests:
            # Determine if this test has executions
            if random.random() > self.config.execution_rate:
                continue

            # Generate 1-5 executions per test
            num_executions = random.randint(1, 5)
            base_date = datetime.now() - timedelta(days=30)

            for j in range(num_executions):
                exec_date = base_date + timedelta(days=random.randint(0, 30))

                # Determine status based on pass rate
                if random.random() < self.config.pass_rate:
                    status = TestStatus.PASSED
                else:
                    status = random.choice([TestStatus.FAILED, TestStatus.BLOCKED])

                execution = {
                    "id": f"{prefix}-{test.get('id', test.get('key'))}-{j:02d}",
                    "testCaseId": test.get("id", test.get("key")),
                    "testCycleName": f"Sprint {(j % 4) + 1}",
                    "status": status.value,
                    "executedOn": exec_date.isoformat() + "Z",
                    "executedBy": random.choice(self.users)["email"],
                    "executionTime": random.randint(1000, 60000),  # 1-60 seconds
                    "actualResult": self._generate_execution_result(status),
                    "comment": self._generate_execution_comment(status) if j % 2 == 0 else None,
                }

                # Add defect links based on status and rate
                if status == TestStatus.FAILED and random.random() < self.config.defect_link_rate:
                    execution["linkedDefects"] = random.sample(self.defects, random.randint(1, 3))
                else:
                    execution["linkedDefects"] = []

                executions.append(execution)

        return executions

    def _hash_project_key_to_id(self) -> int:
        """Generate deterministic project ID from key."""
        hash_obj = hashlib.md5(self.config.project_key.encode())
        return int(hash_obj.hexdigest()[:8], 16) % 1000000

    def _generate_test_name(self, index: int) -> str:
        """Generate realistic test name."""
        actions = ["Verify", "Validate", "Check", "Test", "Ensure"]
        features = [
            "login",
            "checkout",
            "search",
            "payment",
            "profile",
            "dashboard",
            "report",
            "export",
        ]
        conditions = [
            "with valid data",
            "with invalid data",
            "under load",
            "after timeout",
            "with special characters",
        ]

        random.seed(index)
        action = random.choice(actions)
        feature = random.choice(features)
        condition = random.choice(conditions)
        random.seed(self.config.seed)  # Reset seed

        return f"{action} {feature} {condition}"

    def _generate_step_description(self, index: int) -> str:
        """Generate test step description."""
        actions = ["Click", "Enter", "Select", "Navigate to", "Verify", "Wait for"]
        targets = ["button", "field", "dropdown", "page", "element", "modal"]

        action = actions[index % len(actions)]
        target = targets[index % len(targets)]

        return f"{action} the {target}"

    def _generate_execution_result(self, status: TestStatus) -> str:
        """Generate execution result based on status."""
        if status == TestStatus.PASSED:
            return "All steps executed successfully"
        elif status == TestStatus.FAILED:
            return "Step 3 failed: Element not found"
        elif status == TestStatus.BLOCKED:
            return "Test blocked by BUG-1234"
        else:
            return "Test not completed"

    def _generate_execution_comment(self, status: TestStatus) -> str:
        """Generate execution comment."""
        if status == TestStatus.PASSED:
            return "Test passed on first attempt"
        elif status == TestStatus.FAILED:
            return "Failed due to application error, see attached screenshot"
        elif status == TestStatus.BLOCKED:
            return "Blocked by environment issue"
        else:
            return None

    def generate_all_datasets(self, output_dir: str) -> dict[str, str]:
        """Generate all gold master datasets."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        datasets = {}

        # Generate Jira project data
        jira_project = self.generate_jira_project()
        jira_file = output_path / f"gold_jira_{self.config.scenario.value}.json"
        with open(jira_file, "w") as f:
            json.dump(
                {"project": jira_project, "metadata": self._generate_metadata("jira")}, f, indent=2
            )
        datasets["jira"] = str(jira_file)

        # Generate Zephyr data
        zephyr_tests = self.generate_zephyr_tests()
        zephyr_executions = self.generate_test_executions("zephyr")
        zephyr_file = output_path / f"gold_zephyr_{self.config.scenario.value}.json"
        with open(zephyr_file, "w") as f:
            json.dump(
                {
                    "testCases": zephyr_tests,
                    "testExecutions": zephyr_executions,
                    "metadata": self._generate_metadata("zephyr"),
                },
                f,
                indent=2,
            )
        datasets["zephyr"] = str(zephyr_file)

        # Generate qTest data
        qtest_tests = self.generate_qtest_tests()
        qtest_executions = self.generate_test_executions("qtest")
        qtest_file = output_path / f"gold_qtest_{self.config.scenario.value}.json"
        with open(qtest_file, "w") as f:
            json.dump(
                {
                    "testCases": qtest_tests,
                    "testRuns": qtest_executions,
                    "metadata": self._generate_metadata("qtest"),
                },
                f,
                indent=2,
            )
        datasets["qtest"] = str(qtest_file)

        # Generate summary
        summary = self._generate_summary()
        summary_file = output_path / f"gold_summary_{self.config.scenario.value}.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        datasets["summary"] = str(summary_file)

        print(f"\n✅ Generated gold master datasets for '{self.config.scenario.value}' scenario:")
        for vendor, path in datasets.items():
            print(f"  - {vendor}: {path}")

        return datasets

    def _generate_metadata(self, vendor: str) -> dict[str, Any]:
        """Generate metadata for dataset."""
        return {
            "vendor": vendor,
            "scenario": self.config.scenario.value,
            "generated_at": datetime.now().isoformat(),
            "config": asdict(self.config),
            "version": "1.0.0",
        }

    def _generate_summary(self) -> dict[str, Any]:
        """Generate summary statistics."""
        zephyr_tests = self.generate_zephyr_tests()
        qtest_tests = self.generate_qtest_tests()
        zephyr_executions = self.generate_test_executions("zephyr")
        qtest_executions = self.generate_test_executions("qtest")

        # Calculate metrics
        total_tests = len(zephyr_tests) + len(qtest_tests)
        adoption_ratio = len(qtest_tests) / total_tests if total_tests > 0 else 0

        # Count executions
        zephyr_executed = len(set(e["testCaseId"] for e in zephyr_executions))
        qtest_executed = len(set(e["testCaseId"] for e in qtest_executions))

        # Count defects
        defects_linked = sum(
            1 for e in zephyr_executions + qtest_executions if e.get("linkedDefects")
        )

        return {
            "scenario": self.config.scenario.value,
            "statistics": {
                "total_tests": total_tests,
                "zephyr_tests": len(zephyr_tests),
                "qtest_tests": len(qtest_tests),
                "adoption_ratio": round(adoption_ratio, 3),
                "total_executions": len(zephyr_executions) + len(qtest_executions),
                "tests_executed": zephyr_executed + qtest_executed,
                "tests_with_defects": defects_linked,
                "teams": len(self.teams),
                "users": len(self.users),
            },
            "team_breakdown": [
                {
                    "team": team["name"],
                    "adoption_rate": team["adoption_rate"],
                    "component": team["component"],
                }
                for team in self.teams
            ],
        }


def generate_all_scenarios(output_dir: str = "tests/tdm/gold_master"):
    """Generate gold master data for all scenarios."""
    scenarios = [
        GoldMasterConfig(MigrationScenario.FRESH, "PROJ-A", total_tests=300),
        GoldMasterConfig(MigrationScenario.IN_PROGRESS, "PROJ-B", total_tests=500),
        GoldMasterConfig(MigrationScenario.COMPLETE, "PROJ-C", total_tests=400),
        GoldMasterConfig(MigrationScenario.TEAM_BASED, "PROJ-D", total_tests=600),
        GoldMasterConfig(MigrationScenario.EDGE_CASES, "PROJ-E", total_tests=100),
    ]

    all_datasets = {}

    for config in scenarios:
        print(f"\n🔄 Generating '{config.scenario.value}' scenario...")
        generator = GoldMasterGenerator(config)
        datasets = generator.generate_all_datasets(output_dir)
        all_datasets[config.scenario.value] = datasets

    # Generate master manifest
    manifest_file = Path(output_dir) / "gold_master_manifest.json"
    with open(manifest_file, "w") as f:
        json.dump(
            {
                "version": "1.0.0",
                "generated_at": datetime.now().isoformat(),
                "scenarios": all_datasets,
            },
            f,
            indent=2,
        )

    print("\n🎆 Gold master generation complete!")
    print(f"Manifest: {manifest_file}")

    return all_datasets


if __name__ == "__main__":
    # Generate all scenarios
    generate_all_scenarios()
