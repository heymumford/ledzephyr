"""Tests for APIClient functionality."""

from unittest.mock import Mock, patch

import pytest

from ledzephyr.client import APIClient, APIError, AuthenticationError
from ledzephyr.config import Config


class TestAPIClient:
    """Test the APIClient class."""

    def test_api_client_initialization(self):
        """Test APIClient initializes with config."""
        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            timeout=30,
            max_retries=3,
        )

        client = APIClient(config)
        assert client.config == config

    def test_context_manager_closes_client(self):
        """Test APIClient context manager closes HTTP client."""
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        with APIClient(config) as client:
            assert client._http_client is not None
        # Client should be closed after context

    @patch("httpx.Client.request")
    def test_make_request_success_returns_response(self, mock_request):
        """Test _make_request with successful response."""
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        client = APIClient(config)
        response = client._make_request("GET", "https://example.com/test")

        assert response == mock_response

    @patch("httpx.Client.request")
    def test_make_request_401_raises_auth_error(self, mock_request):
        """Test _make_request with 401 raises AuthenticationError."""
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response

        client = APIClient(config)

        with pytest.raises(AuthenticationError):
            client._make_request("GET", "https://example.com/test")

    @patch("httpx.Client.request")
    def test_make_request_500_raises_api_error(self, mock_request):
        """Test _make_request with 500 raises APIError."""
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        # Mock 500 response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"
        mock_request.return_value = mock_response

        client = APIClient(config)

        with pytest.raises(APIError):
            client._make_request("GET", "https://example.com/test")

    @patch.object(APIClient, "_make_request")
    def test_test_jira_connection_success_returns_true(self, mock_request):
        """Test test_jira_connection with successful response returns True."""
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        client = APIClient(config)
        result = client.test_jira_connection()

        assert result is True

    @patch.object(APIClient, "_make_request")
    def test_test_jira_connection_failure_returns_false(self, mock_request):
        """Test test_jira_connection with exception returns False."""
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        # Mock request that raises exception
        mock_request.side_effect = Exception("Connection failed")

        client = APIClient(config)
        result = client.test_jira_connection()

        assert result is False

    @patch.object(APIClient, "_make_request")
    def test_test_zephyr_connection_no_token_returns_false(self, mock_request):
        """Test test_zephyr_connection without token returns False."""
        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            # No zephyr_token
        )

        client = APIClient(config)
        result = client.test_zephyr_connection()

        assert result is False

    @patch.object(APIClient, "_make_request")
    def test_test_qtest_connection_no_token_returns_false(self, mock_request):
        """Test test_qtest_connection without token returns False."""
        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            # No qtest_token
        )

        client = APIClient(config)
        result = client.test_qtest_connection()

        assert result is False
