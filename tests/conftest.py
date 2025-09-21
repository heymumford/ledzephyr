"""Global test configuration and fixtures for ledzephyr."""

import hashlib
import json
import os
import tempfile
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from hypothesis import Verbosity, settings

# Deterministic seeds for reproducible tests
DETERMINISTIC_SEED = 42
os.environ["PYTHONHASHSEED"] = str(DETERMINISTIC_SEED)


# Hypothesis configuration for property-based testing
settings.register_profile("ci", max_examples=50, verbosity=Verbosity.verbose)
settings.register_profile("dev", max_examples=10)
settings.register_profile("exhaustive", max_examples=1000)

# Use CI profile by default, dev for local development
profile = os.getenv("HYPOTHESIS_PROFILE", "ci")
settings.load_profile(profile)


@pytest.fixture(scope="session")
def tdm_schema() -> dict[str, Any]:
    """Load the TDM manifest schema."""
    schema_path = Path(__file__).parent.parent / "tdm" / "schema" / "manifest.schema.json"
    with open(schema_path) as f:
        return json.load(f)


@pytest.fixture
def temp_manifest_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test manifests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_manifest() -> dict[str, Any]:
    """Provide a valid sample manifest for testing."""
    return {
        "dataset_id": "test-dataset-2025",
        "as_of": "2025-06-30T23:59:59Z",
        "sources": {
            "jira": {"mode": "stub", "preset": "basic_project"},
            "zephyr": {"mode": "fake", "config": {"total_tests": 100}},
        },
        "normalization": {"currency": "USD", "timezone": "UTC", "rounding": "HALF_UP"},
        "quality_gates": {"schema_compliance": "error", "completeness_min": 0.95},
    }


@pytest.fixture
def fixed_datetime():
    """Provide a fixed datetime for deterministic testing."""
    return datetime(2025, 6, 30, 23, 59, 59, tzinfo=UTC)


@pytest.fixture
def deterministic_hash():
    """Create deterministic hash function for testing."""

    def _hash(data: str) -> str:
        return hashlib.sha256(f"test_salt_{data}".encode()).hexdigest()[:16]

    return _hash


@pytest.fixture
def mock_api_client():
    """Create a mock API client for testing."""
    client = Mock()
    client.get_jira_project.return_value = Mock(
        key="TEST", name="Test Project", components=["Frontend", "Backend"]
    )
    client.get_zephyr_tests.return_value = []
    client.get_qtest_tests.return_value = []
    client.get_test_executions.return_value = {}
    return client


@pytest.fixture
def sample_test_data():
    """Provide sample test case data for calculations."""
    from datetime import datetime

    from ledzephyr.models import TestCase

    now = datetime.now()
    return [
        TestCase(
            id="Z-1",
            key="Z-1",
            summary="Zephyr Test 1",
            project_key="TEST",
            component="Frontend",
            labels=["ui", "critical"],
            assignee="alice@example.com",
            source_system="zephyr",
            created=now,
            updated=now,
            status="Done",
            last_execution=now,
            execution_status="PASS",
        ),
        TestCase(
            id="Q-1",
            key="Q-1",
            summary="qTest Test 1",
            project_key="TEST",
            component="Backend",
            labels=["api", "integration"],
            assignee="bob@example.com",
            source_system="qtest",
            created=now,
            updated=now,
            status="In Progress",
            last_execution=None,
            execution_status=None,
        ),
    ]


@pytest.fixture(autouse=True)
def isolate_random_state():
    """Ensure each test starts with deterministic random state."""
    import random

    import numpy as np

    random.seed(DETERMINISTIC_SEED)
    np.random.seed(DETERMINISTIC_SEED)


# Test markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests with doubles")
    config.addinivalue_line("markers", "e2e: End-to-end tests with manifests")
    config.addinivalue_line("markers", "golden: Tests with golden file comparisons")
    config.addinivalue_line("markers", "property: Property-based tests with Hypothesis")
    config.addinivalue_line("markers", "snapshot: Tests using snapshot comparisons")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark tests based on file path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)

        # Mark golden and property tests based on function names
        if "golden" in item.name:
            item.add_marker(pytest.mark.golden)
        if "property" in item.name:
            item.add_marker(pytest.mark.property)
        if "snapshot" in item.name:
            item.add_marker(pytest.mark.snapshot)
