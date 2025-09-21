"""Shared test fixtures following testing standards."""

import os
import random
from typing import Any

import pytest
from freezegun import freeze_time

from ledzephyr.models import ProjectMetrics, TeamMetrics, TrendData


@pytest.fixture(scope="session", autouse=True)
def _set_seeds():
    """Set deterministic seeds for reproducible tests."""
    os.environ.setdefault("PYTHONHASHSEED", "0")
    random.seed(0)


@pytest.fixture(autouse=True)
def _no_network(request):
    """Disable network access in unit tests."""
    # Skip network isolation for integration tests with enable_socket marker
    if request.node.get_closest_marker("enable_socket"):
        return
    # For other tests, network is disabled by default via pytest-socket
    # This fixture documents the intent and can be customized per test


@pytest.fixture
def frozen_time():
    """Provide a frozen time context for deterministic time-dependent tests."""
    with freeze_time("2024-01-15 10:00:00") as frozen:
        yield frozen


@pytest.fixture
def sample_project_metrics():
    """Factory for creating sample ProjectMetrics."""

    def make(**kwargs) -> ProjectMetrics:
        defaults = {
            "project_key": "DEMO",
            "time_window": "7d",
            "total_tests": 100,
            "qtest_tests": 40,
            "zephyr_tests": 60,
            "adoption_ratio": 0.4,
            "active_users": 8,
            "coverage_parity": 0.85,
            "defect_link_rate": 0.12,
        }
        return ProjectMetrics(**{**defaults, **kwargs})

    return make


@pytest.fixture
def sample_trend_data():
    """Factory for creating sample TrendData."""

    def make(**kwargs) -> TrendData:
        defaults = {
            "week_1": {"adoption_ratio": 0.45, "coverage_parity": 0.85, "active_users": 8},
            "week_2": {"adoption_ratio": 0.42, "coverage_parity": 0.83, "active_users": 7},
            "week_3": {"adoption_ratio": 0.40, "coverage_parity": 0.82, "active_users": 6},
            "week_4": {"adoption_ratio": 0.38, "coverage_parity": 0.80, "active_users": 5},
            "adoption_trend": 0.07,
            "coverage_trend": 0.05,
            "activity_trend": 3.0,
        }
        return TrendData(**{**defaults, **kwargs})

    return make


@pytest.fixture
def sample_team_metrics():
    """Factory for creating sample TeamMetrics."""

    def make(**kwargs) -> TeamMetrics:
        defaults = {
            "team_name": "Team Alpha",
            "team_source": "component",
            "total_tests": 50,
            "qtest_tests": 20,
            "zephyr_tests": 30,
            "adoption_ratio": 0.4,
            "active_users": 4,
            "coverage_parity": 0.85,
            "defect_link_rate": 0.1,
        }
        return TeamMetrics(**{**defaults, **kwargs})

    return make


@pytest.fixture
def mock_config():
    """Factory for creating mock configuration data."""

    def make(**kwargs) -> dict[str, Any]:
        defaults = {
            "jira_url": "https://example.atlassian.net",
            "jira_username": "demo@example.com",
            "jira_api_token": "fake_token",
            "zephyr_url": "https://example.atlassian.net",
            "zephyr_token": "fake_token",
            "qtest_url": "https://example.qtestnet.com",
            "qtest_token": "fake_token",
            "timeout": 30,
            "max_retries": 3,
            "log_level": "INFO",
        }
        return {**defaults, **kwargs}

    return make


@pytest.fixture
def temp_env(monkeypatch):
    """Provide temporary environment variable manipulation."""

    def set_env(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(key, str(value))

    return set_env


@pytest.fixture
def mock_responses():
    """Provide HTTP response mocking capabilities."""
    # This would integrate with responses library when needed
    responses = {}

    def add_response(url: str, json_data: dict[str, Any], status: int = 200):
        responses[url] = {"json": json_data, "status": status}

    def get_response(url: str):
        return responses.get(url, {"json": {}, "status": 404})

    return type(
        "MockResponses",
        (),
        {
            "add": add_response,
            "get": get_response,
            "responses": responses,
        },
    )()
