"""
Data masking and tokenization for sensitive test data.
"""

import hashlib
import json
import re
from datetime import datetime
from typing import Any


class DataMasker:
    """Deterministic data masking for test data."""

    def __init__(self, salt: str = "ledzephyr-test-salt-2024"):
        """Initialize with a salt for deterministic masking."""
        self.salt = salt
        self.token_map: dict[str, str] = {}  # Original -> Token mapping
        self.reverse_map: dict[str, str] = {}  # Token -> Original (for debugging)
        self.token_counter = 0

    def mask(self, value: Any, strategy: str = "tokenize") -> Any:
        """Apply masking strategy to a value."""
        if value is None:
            return None

        if strategy == "none":
            return value
        elif strategy == "tokenize":
            return self._tokenize(value)
        elif strategy == "redact":
            return self._redact(value)
        elif strategy == "hash":
            return self._hash(value)
        elif strategy == "partial":
            return self._partial_mask(value)
        elif strategy == "synthetic":
            return self._synthetic(value)
        else:
            raise ValueError(f"Unknown masking strategy: {strategy}")

    def _tokenize(self, value: Any) -> str:
        """Replace with deterministic token."""
        str_value = str(value)

        if str_value in self.token_map:
            return self.token_map[str_value]

        # Generate deterministic token
        self.token_counter += 1
        token = f"TOKEN_{self.token_counter:06d}"

        self.token_map[str_value] = token
        self.reverse_map[token] = str_value

        return token

    def _redact(self, value: Any) -> str:
        """Completely redact the value."""
        return "[REDACTED]"

    def _hash(self, value: Any) -> str:
        """One-way hash the value."""
        str_value = str(value)
        hasher = hashlib.sha256()
        hasher.update(f"{self.salt}{str_value}".encode())
        return hasher.hexdigest()[:16]  # Use first 16 chars

    def _partial_mask(self, value: Any) -> str:
        """Partially mask the value (show last 4 chars)."""
        str_value = str(value)

        # Email handling
        if "@" in str_value:
            parts = str_value.split("@")
            if len(parts[0]) > 2:
                masked_user = parts[0][:2] + "***"
            else:
                masked_user = "***"
            return f"{masked_user}@{parts[1]}"

        # Phone number handling
        if re.match(r"^[\d\s\-\+\(\)]+$", str_value) and len(str_value) >= 10:
            return "***-***-" + str_value[-4:]

        # Default: show last 4 characters
        if len(str_value) > 4:
            return "*" * (len(str_value) - 4) + str_value[-4:]
        else:
            return "*" * len(str_value)

    def _synthetic(self, value: Any) -> str:
        """Replace with synthetic but realistic data."""
        str_value = str(value)

        # Email handling
        if "@" in str_value:
            domain = str_value.split("@")[1] if "@" in str_value else "example.com"
            user_hash = hashlib.md5(f"{self.salt}{str_value}".encode()).hexdigest()[:8]
            return f"user_{user_hash}@{domain}"

        # Name handling (simple heuristic)
        if str_value.istitle() and " " not in str_value and len(str_value) < 20:
            names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
            index = hash(f"{self.salt}{str_value}") % len(names)
            return names[index]

        # ID handling
        if str_value.isdigit():
            # Generate consistent synthetic ID
            return str(hash(f"{self.salt}{str_value}") % 1000000)

        # Default: use hash-based synthetic
        return f"SYNTH_{self._hash(value)[:8]}"

    def mask_dict(self, data: dict[str, Any], field_masks: dict[str, str]) -> dict[str, Any]:
        """Mask fields in a dictionary based on field mask mapping."""
        masked = {}

        for key, value in data.items():
            if key in field_masks:
                masked[key] = self.mask(value, field_masks[key])
            elif isinstance(value, dict):
                # Recursively mask nested dicts
                nested_masks = {
                    k.split(".", 1)[1]: v for k, v in field_masks.items() if k.startswith(f"{key}.")
                }
                masked[key] = self.mask_dict(value, nested_masks) if nested_masks else value
            elif isinstance(value, list):
                # Handle lists
                masked[key] = [
                    self.mask_dict(item, field_masks) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                masked[key] = value

        return masked

    def mask_dataset(
        self, dataset: list[dict[str, Any]], field_masks: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Mask an entire dataset."""
        return [self.mask_dict(record, field_masks) for record in dataset]

    def get_token_mapping(self) -> dict[str, str]:
        """Get the token mapping for reference."""
        return self.token_map.copy()

    def save_mapping(self, filepath: str):
        """Save token mapping to file (for debugging/reference only)."""
        with open(filepath, "w") as f:
            json.dump(
                {
                    "token_map": self.token_map,
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "total_tokens": len(self.token_map),
                    },
                },
                f,
                indent=2,
            )


class GoldenDataGenerator:
    """Generate deterministic golden test data."""

    def __init__(self, seed: int = 42):
        """Initialize with a seed for deterministic generation."""
        self.seed = seed
        self.counter = 0

    def generate_jira_issues(self, count: int = 10) -> list[dict[str, Any]]:
        """Generate deterministic Jira issues."""
        issues = []
        statuses = ["Open", "In Progress", "Done", "Blocked"]
        priorities = ["High", "Medium", "Low"]
        types = ["Bug", "Story", "Task", "Epic"]

        for i in range(count):
            issue = {
                "id": f"GOLD-{1000 + i}",
                "key": f"TEST-{i + 1}",
                "fields": {
                    "summary": f"Golden test issue {i + 1}",
                    "description": f"This is a deterministic test issue number {i + 1}",
                    "status": {"name": statuses[i % len(statuses)]},
                    "priority": {"name": priorities[i % len(priorities)]},
                    "issuetype": {"name": types[i % len(types)]},
                    "assignee": (
                        {
                            "accountId": f"user-{i % 3}",
                            "emailAddress": f"user{i % 3}@golden.test",
                            "displayName": f"Test User {i % 3}",
                        }
                        if i % 2 == 0
                        else None
                    ),
                    "reporter": {
                        "accountId": "reporter-1",
                        "emailAddress": "reporter@golden.test",
                        "displayName": "Test Reporter",
                    },
                    "created": f"2024-01-{(i % 28) + 1:02d}T{(i % 24):02d}:00:00Z",
                    "updated": f"2024-01-{(i % 28) + 2:02d}T{(i % 24):02d}:00:00Z",
                    "labels": ["golden", "test"] if i % 3 == 0 else ["golden"],
                    "components": [{"name": "Backend" if i % 2 == 0 else "Frontend"}],
                },
            }
            issues.append(issue)

        return issues

    def generate_zephyr_testcases(self, count: int = 10) -> list[dict[str, Any]]:
        """Generate deterministic Zephyr test cases."""
        testcases = []
        statuses = ["Draft", "Approved", "Deprecated"]
        priorities = ["Critical", "High", "Medium", "Low"]

        for i in range(count):
            testcase = {
                "id": f"Z-TC-GOLD-{i + 1:04d}",
                "key": f"Z-TC-{i + 1:04d}",
                "name": f"Golden Test Case {i + 1}",
                "projectId": 10001,
                "status": statuses[i % len(statuses)],
                "priority": priorities[i % len(priorities)],
                "labels": ["golden", "automated"] if i % 2 == 0 else ["golden", "manual"],
                "component": "Backend" if i % 2 == 0 else "Frontend",
                "estimatedTime": 300000 + (i * 60000),  # 5-15 minutes
                "steps": [
                    {
                        "order": j + 1,
                        "description": f"Step {j + 1} for test case {i + 1}",
                        "expected": f"Expected result {j + 1}",
                    }
                    for j in range(3 + (i % 3))  # 3-5 steps per test case
                ],
                "createdOn": f"2024-01-01T{(i % 24):02d}:00:00Z",
                "updatedOn": f"2024-01-02T{(i % 24):02d}:00:00Z",
            }
            testcases.append(testcase)

        return testcases

    def generate_qtest_testcases(self, count: int = 10) -> list[dict[str, Any]]:
        """Generate deterministic qTest test cases."""
        testcases = []
        types = ["Functional", "Regression", "Smoke", "Integration"]
        automation = ["Automated", "Manual", "Semi-Automated"]

        for i in range(count):
            testcase = {
                "id": 100000 + i,
                "name": f"Golden qTest Case {i + 1}",
                "description": f"Deterministic test case {i + 1} for qTest",
                "test_case_version_id": 200000 + i,
                "project_id": 12345,
                "properties": [
                    {"field_id": 1, "field_value": automation[i % len(automation)]},
                    {"field_id": 2, "field_value": types[i % len(types)]},
                    {"field_id": 3, "field_value": "High" if i % 3 == 0 else "Medium"},
                ],
                "test_steps": [
                    {
                        "order": j + 1,
                        "description": f"Golden step {j + 1}",
                        "expected_result": f"Golden expected {j + 1}",
                        "actual_result": None,
                    }
                    for j in range(2 + (i % 4))  # 2-5 steps
                ],
                "created_date": f"2024-01-{(i % 28) + 1:02d}T00:00:00Z",
                "last_modified_date": f"2024-01-{(i % 28) + 2:02d}T00:00:00Z",
            }
            testcases.append(testcase)

        return testcases

    def save_golden_data(self, output_dir: str):
        """Save all golden data to files."""
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate and save Jira data
        jira_data = {
            "issues": self.generate_jira_issues(25),
            "metadata": {
                "type": "golden",
                "vendor": "jira",
                "generated_at": datetime.now().isoformat(),
                "record_count": 25,
            },
        }
        with open(output_path / "golden_jira.json", "w") as f:
            json.dump(jira_data, f, indent=2)

        # Generate and save Zephyr data
        zephyr_data = {
            "testcases": self.generate_zephyr_testcases(20),
            "metadata": {
                "type": "golden",
                "vendor": "zephyr",
                "generated_at": datetime.now().isoformat(),
                "record_count": 20,
            },
        }
        with open(output_path / "golden_zephyr.json", "w") as f:
            json.dump(zephyr_data, f, indent=2)

        # Generate and save qTest data
        qtest_data = {
            "testcases": self.generate_qtest_testcases(30),
            "metadata": {
                "type": "golden",
                "vendor": "qtest",
                "generated_at": datetime.now().isoformat(),
                "record_count": 30,
            },
        }
        with open(output_path / "golden_qtest.json", "w") as f:
            json.dump(qtest_data, f, indent=2)

        print(f"Golden data saved to {output_path}")
        return output_path
