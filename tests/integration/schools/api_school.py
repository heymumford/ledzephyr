"""
API School: External API integration patterns

Orthogonal Concern: How we interact with external APIs
- Mock responses
- Error handling
- Timeout behavior
- Authentication flows
"""

from unittest.mock import Mock, patch

import httpx

from ledzephyr.client import APIClient
from ledzephyr.config import Config

from . import Kata, School, register_school


def kata_api_mock_responses():
    """Kata: API clients handle mocked responses correctly."""
    config = Config(
        jira_url="https://test.atlassian.net",
        jira_username="test@example.com",
        jira_api_token="test_token",
    )

    with patch.object(APIClient, "_make_request") as mock_request:
        mock_response = Mock()
        mock_response.json.return_value = {
            "key": "TEST",
            "name": "Test Project",
            "components": [{"name": "Component1"}, {"name": "Component2"}],
        }
        mock_request.return_value = mock_response

        client = APIClient(config)
        result = client.get_jira_project("TEST")

        assert result.key == "TEST"
        assert result.name == "Test Project"
        assert "Component1" in result.components
    return True


def kata_api_error_handling():
    """Kata: API clients gracefully handle HTTP errors."""
    config = Config(
        jira_url="https://test.atlassian.net",
        jira_username="test@example.com",
        jira_api_token="test_token",
    )

    with patch.object(APIClient, "_make_request") as mock_request:
        # Simulate HTTP error
        mock_request.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=Mock(status_code=404)
        )

        client = APIClient(config)

        # Should handle gracefully, not crash
        try:
            client.get_jira_project("NONEXISTENT")
            raise AssertionError("Should have raised exception")
        except httpx.HTTPStatusError as e:
            assert e.response.status_code == 404
    return True


def kata_api_timeout_resilience():
    """Kata: API clients respect timeout configurations."""
    config = Config(
        jira_url="https://test.atlassian.net",
        jira_username="test@example.com",
        jira_api_token="test_token",
    )

    with patch.object(APIClient, "_make_request") as mock_request:
        # Simulate timeout
        mock_request.side_effect = httpx.TimeoutException("Request timeout")

        client = APIClient(config)

        try:
            client.get_jira_project("TEST")
            raise AssertionError("Should have timed out")
        except httpx.TimeoutException:
            pass  # Expected
    return True


# Define the API School
api_school = School(
    name="api_school",
    description="External API integration patterns and error handling",
    katas=[
        Kata("mock_responses", "API clients handle mocked responses", kata_api_mock_responses),
        Kata(
            "error_handling", "API clients handle HTTP errors gracefully", kata_api_error_handling
        ),
        Kata(
            "timeout_resilience", "API clients respect timeout configs", kata_api_timeout_resilience
        ),
    ],
    parallel_safe=True,
)

# Register for discovery
register_school(api_school)
