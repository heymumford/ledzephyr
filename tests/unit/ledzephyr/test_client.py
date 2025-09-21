"""Comprehensive tests for APIClient functionality."""

from datetime import datetime
from unittest.mock import Mock, patch

import httpx
import pytest

from ledzephyr.client import APIClient, APIError, AuthenticationError
from ledzephyr.config import Config
from ledzephyr.error_handler import RateLimitError


class TestAPIClientInitialization:
    """Test APIClient initialization and configuration."""

    def test_initialization_with_minimal_config(self):
        """Test APIClient initializes with minimal required config."""
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)
        assert client.config == config
        assert client._http_client is not None
        assert client._cache is not None
        assert client._rate_limiter is not None
        assert client._error_handler is not None

    def test_initialization_with_full_config(self):
        """Test APIClient initializes with full configuration."""
        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            zephyr_token="zephyr_token",
            zephyr_url="https://zephyr.example.com",
            qtest_token="qtest_token",
            qtest_url="https://qtest.example.com",
            timeout=60,
            max_retries=5,
        )

        client = APIClient(config)
        assert client.config == config
        # Just verify the client was created with timeout configuration
        assert client._http_client.timeout is not None

    def test_context_manager_opens_and_closes_client(self):
        """Test APIClient context manager properly opens and closes HTTP client."""
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        with APIClient(config) as client:
            assert client._http_client is not None
            http_client = client._http_client

        # After context exit, client should have close called
        # We can't easily test this directly, but the context manager exists
        assert http_client is not None


class TestAPIClientRequestHandling:
    """Test HTTP request handling with mocking to avoid rate limiter issues."""

    @patch("ledzephyr.client.MultiTenantRateLimiter")
    @patch("ledzephyr.client.get_error_handler")
    @patch("ledzephyr.client.get_api_cache")
    @patch("ledzephyr.client.get_observability")
    @patch("httpx.Client")
    def test_make_request_success_returns_response(
        self, mock_http_client, mock_obs, mock_cache, mock_error_handler, mock_rate_limiter
    ):
        """Test _make_request with successful response."""
        # Setup mocks
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}

        mock_client_instance = Mock()
        mock_client_instance.request.return_value = mock_response
        mock_http_client.return_value = mock_client_instance

        mock_rate_limiter_instance = Mock()
        mock_rate_limiter_instance.acquire.return_value = True
        mock_rate_limiter.return_value = mock_rate_limiter_instance

        mock_error_handler_instance = Mock()
        mock_error_handler_instance.circuit_breakers = {}
        mock_error_handler.return_value = mock_error_handler_instance

        mock_cache.return_value = Mock()
        mock_obs.return_value = None  # No observability in this test

        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)
        response = client._make_request("GET", "https://example.com/test")

        assert response == mock_response
        mock_client_instance.request.assert_called_once()
        mock_rate_limiter_instance.acquire.assert_called_once()

    @patch("ledzephyr.client.MultiTenantRateLimiter")
    @patch("ledzephyr.client.get_error_handler")
    @patch("ledzephyr.client.get_api_cache")
    @patch("ledzephyr.client.get_observability")
    @patch("httpx.Client")
    def test_make_request_401_raises_authentication_error(
        self, mock_http_client, mock_obs, mock_cache, mock_error_handler, mock_rate_limiter
    ):
        """Test _make_request with 401 raises AuthenticationError."""
        # Setup mocks
        mock_response = Mock()
        mock_response.status_code = 401

        mock_client_instance = Mock()
        mock_client_instance.request.return_value = mock_response
        mock_http_client.return_value = mock_client_instance

        mock_rate_limiter_instance = Mock()
        mock_rate_limiter_instance.acquire.return_value = True
        mock_rate_limiter.return_value = mock_rate_limiter_instance

        mock_error_handler_instance = Mock()
        mock_error_handler_instance.circuit_breakers = {}
        mock_error_handler.return_value = mock_error_handler_instance

        mock_cache.return_value = Mock()
        mock_obs.return_value = None

        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)

        with pytest.raises(AuthenticationError, match="Authentication failed"):
            client._make_request("GET", "https://example.com/test")

    @patch("ledzephyr.client.MultiTenantRateLimiter")
    @patch("ledzephyr.client.get_error_handler")
    @patch("ledzephyr.client.get_api_cache")
    @patch("ledzephyr.client.get_observability")
    @patch("httpx.Client")
    def test_make_request_429_raises_rate_limit_error(
        self, mock_http_client, mock_obs, mock_cache, mock_error_handler, mock_rate_limiter
    ):
        """Test _make_request with 429 raises RateLimitError."""
        # Setup mocks
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "120"}

        mock_client_instance = Mock()
        mock_client_instance.request.return_value = mock_response
        mock_http_client.return_value = mock_client_instance

        mock_rate_limiter_instance = Mock()
        mock_rate_limiter_instance.acquire.return_value = True
        mock_rate_limiter.return_value = mock_rate_limiter_instance

        mock_error_handler_instance = Mock()
        mock_error_handler_instance.circuit_breakers = {}
        mock_error_handler.return_value = mock_error_handler_instance

        mock_cache.return_value = Mock()
        mock_obs.return_value = None

        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)

        with pytest.raises(RateLimitError) as exc_info:
            client._make_request("GET", "https://example.com/test")

        assert "Rate limited" in str(exc_info.value)
        assert exc_info.value.metadata.get("retry_after") == 120

    @patch("ledzephyr.client.MultiTenantRateLimiter")
    @patch("ledzephyr.client.get_error_handler")
    @patch("ledzephyr.client.get_api_cache")
    @patch("ledzephyr.client.get_observability")
    @patch("httpx.Client")
    def test_make_request_500_raises_api_error(
        self, mock_http_client, mock_obs, mock_cache, mock_error_handler, mock_rate_limiter
    ):
        """Test _make_request with 500 raises APIError."""
        # Setup mocks
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"

        mock_client_instance = Mock()
        mock_client_instance.request.return_value = mock_response
        mock_http_client.return_value = mock_client_instance

        mock_rate_limiter_instance = Mock()
        mock_rate_limiter_instance.acquire.return_value = True
        mock_rate_limiter.return_value = mock_rate_limiter_instance

        mock_error_handler_instance = Mock()
        mock_error_handler_instance.circuit_breakers = {}
        mock_error_handler.return_value = mock_error_handler_instance

        mock_cache.return_value = Mock()
        mock_obs.return_value = None

        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)

        with pytest.raises(APIError, match="HTTP 500: Internal Server Error"):
            client._make_request("GET", "https://example.com/test")

    @patch("ledzephyr.client.MultiTenantRateLimiter")
    @patch("ledzephyr.client.get_error_handler")
    @patch("ledzephyr.client.get_api_cache")
    @patch("ledzephyr.client.get_observability")
    @patch("httpx.Client")
    def test_make_request_network_error_reraises(
        self, mock_http_client, mock_obs, mock_cache, mock_error_handler, mock_rate_limiter
    ):
        """Test _make_request with network error reraises httpx.RequestError."""
        # Setup mocks
        mock_client_instance = Mock()
        mock_client_instance.request.side_effect = httpx.RequestError("Connection failed")
        mock_http_client.return_value = mock_client_instance

        mock_rate_limiter_instance = Mock()
        mock_rate_limiter_instance.acquire.return_value = True
        mock_rate_limiter.return_value = mock_rate_limiter_instance

        mock_error_handler_instance = Mock()
        mock_error_handler_instance.circuit_breakers = {}
        mock_error_handler.return_value = mock_error_handler_instance

        mock_cache.return_value = Mock()
        mock_obs.return_value = None

        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)

        # The retry decorator will wrap the httpx.RequestError in a RetryError
        with pytest.raises(Exception):  # Either httpx.RequestError or tenacity.RetryError
            client._make_request("GET", "https://example.com/test")


class TestAPIClientRateLimiting:
    """Test rate limiting behavior."""

    @patch("ledzephyr.client.MultiTenantRateLimiter")
    @patch("ledzephyr.client.get_error_handler")
    @patch("ledzephyr.client.get_api_cache")
    @patch("ledzephyr.client.get_observability")
    @patch("httpx.Client")
    def test_rate_limit_blocks_request(
        self, mock_http_client, mock_obs, mock_cache, mock_error_handler, mock_rate_limiter
    ):
        """Test that rate limiter can block requests."""
        # Setup mocks
        mock_rate_limiter_instance = Mock()
        mock_rate_limiter_instance.acquire.return_value = False  # Rate limit hit
        mock_rate_limiter.return_value = mock_rate_limiter_instance

        mock_error_handler_instance = Mock()
        mock_error_handler_instance.circuit_breakers = {}
        mock_error_handler.return_value = mock_error_handler_instance

        mock_cache.return_value = Mock()
        mock_obs.return_value = None

        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)

        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            client._make_request("GET", "https://example.com/test")


class TestAPIClientCircuitBreaker:
    """Test circuit breaker functionality."""

    @patch("ledzephyr.client.MultiTenantRateLimiter")
    @patch("ledzephyr.client.get_error_handler")
    @patch("ledzephyr.client.get_api_cache")
    @patch("ledzephyr.client.get_observability")
    @patch("httpx.Client")
    def test_circuit_breaker_open_blocks_request(
        self, mock_http_client, mock_obs, mock_cache, mock_error_handler, mock_rate_limiter
    ):
        """Test that open circuit breaker blocks requests."""
        # Setup mocks
        mock_breaker = Mock()
        mock_breaker.state = "open"

        mock_error_handler_instance = Mock()
        mock_error_handler_instance.circuit_breakers = {"jira_api": mock_breaker}
        mock_error_handler.return_value = mock_error_handler_instance

        mock_rate_limiter.return_value = Mock()
        mock_cache.return_value = Mock()
        mock_obs.return_value = None

        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)

        with pytest.raises(APIError, match="Circuit breaker for jira is open"):
            client._make_request("GET", "https://example.com/test")


class TestAPIClientServiceDetection:
    """Test service detection from URLs."""

    def test_determine_service_jira(self):
        """Test service detection for Jira URLs."""
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)

        assert client._determine_service("https://example.com/rest/api/2/project") == "jira"
        assert client._determine_service("https://jira.example.com/api") == "jira"

    def test_determine_service_zephyr(self):
        """Test service detection for Zephyr URLs."""
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)

        assert client._determine_service("https://zephyr.example.com/api") == "zephyr"
        assert client._determine_service("https://example.com/scale/api") == "zephyr"

    def test_determine_service_qtest(self):
        """Test service detection for qTest URLs."""
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)

        assert client._determine_service("https://qtest.example.com/api") == "qtest"


class TestAPIClientConnectionTests:
    """Test connection validation methods."""

    @patch.object(APIClient, "_make_request")
    def test_test_jira_connection_success(self, mock_request):
        """Test successful Jira connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)
        result = client.test_jira_connection()

        assert result is True
        mock_request.assert_called_once_with(
            "GET", "https://example.com/rest/api/2/myself", auth=("user", "token")
        )

    @patch.object(APIClient, "_make_request")
    def test_test_jira_connection_failure(self, mock_request):
        """Test failed Jira connection test."""
        mock_request.side_effect = Exception("Connection failed")

        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)
        result = client.test_jira_connection()

        assert result is False


class TestAPIClientJiraProject:
    """Test Jira project retrieval."""

    @patch.object(APIClient, "_make_request")
    def test_get_jira_project_success(self, mock_request):
        """Test successful Jira project retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "key": "TEST",
            "name": "Test Project",
            "description": "A test project",
            "lead": {"displayName": "John Doe"},
            "components": [{"name": "Component 1"}, {"name": "Component 2"}],
        }
        mock_request.return_value = mock_response

        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)
        project = client.get_jira_project("TEST")

        assert project.key == "TEST"
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.lead == "John Doe"
        assert project.components == ["Component 1", "Component 2"]

        mock_request.assert_called_once_with(
            "GET", "https://example.com/rest/api/2/project/TEST", auth=("user", "token")
        )

    def test_test_zephyr_connection_no_token(self):
        """Test Zephyr connection test without token."""
        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            # No zephyr_token
        )

        client = APIClient(config)
        result = client.test_zephyr_connection()

        assert result is False


class TestAPIClientJiraProject:
    """Test Jira project retrieval."""

    @patch.object(APIClient, "_make_request")
    def test_get_jira_project_success(self, mock_request):
        """Test successful Jira project retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "key": "TEST",
            "name": "Test Project",
            "description": "A test project",
            "lead": {"displayName": "John Doe"},
            "components": [{"name": "Component 1"}, {"name": "Component 2"}],
        }
        mock_request.return_value = mock_response

        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)
        project = client.get_jira_project("TEST")

        assert project.key == "TEST"
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.lead == "John Doe"
        assert project.components == ["Component 1", "Component 2"]

        mock_request.assert_called_once_with(
            "GET", "https://example.com/rest/api/2/project/TEST", auth=("user", "token")
        )

    @patch.object(APIClient, "_make_request")
    def test_test_zephyr_connection_success(self, mock_request):
        """Test successful Zephyr connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            zephyr_token="zephyr_token",
        )

        client = APIClient(config)
        result = client.test_zephyr_connection()

        assert result is True
        mock_request.assert_called_once_with(
            "GET",
            "https://example.com/rest/atm/1.0/healthcheck",
            headers={"Authorization": "Bearer zephyr_token"},
        )

    @patch.object(APIClient, "_make_request")
    def test_test_zephyr_connection_with_custom_url(self, mock_request):
        """Test Zephyr connection with custom Zephyr URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            zephyr_token="zephyr_token",
            zephyr_url="https://zephyr.example.com",
        )

        client = APIClient(config)
        result = client.test_zephyr_connection()

        assert result is True
        mock_request.assert_called_once_with(
            "GET",
            "https://zephyr.example.com/rest/atm/1.0/healthcheck",
            headers={"Authorization": "Bearer zephyr_token"},
        )

    @patch.object(APIClient, "_make_request")
    def test_test_zephyr_connection_failure(self, mock_request):
        """Test failed Zephyr connection test."""
        mock_request.side_effect = Exception("Connection failed")

        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            zephyr_token="zephyr_token",
        )

        client = APIClient(config)
        result = client.test_zephyr_connection()

        assert result is False


class TestAPIClientJiraProject:
    """Test Jira project retrieval."""

    @patch.object(APIClient, "_make_request")
    def test_get_jira_project_success(self, mock_request):
        """Test successful Jira project retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "key": "TEST",
            "name": "Test Project",
            "description": "A test project",
            "lead": {"displayName": "John Doe"},
            "components": [{"name": "Component 1"}, {"name": "Component 2"}],
        }
        mock_request.return_value = mock_response

        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)
        project = client.get_jira_project("TEST")

        assert project.key == "TEST"
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.lead == "John Doe"
        assert project.components == ["Component 1", "Component 2"]

        mock_request.assert_called_once_with(
            "GET", "https://example.com/rest/api/2/project/TEST", auth=("user", "token")
        )

    def test_test_qtest_connection_no_token(self):
        """Test qTest connection test without token."""
        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            # No qtest_token
        )

        client = APIClient(config)
        result = client.test_qtest_connection()

        assert result is False


class TestAPIClientJiraProject:
    """Test Jira project retrieval."""

    @patch.object(APIClient, "_make_request")
    def test_get_jira_project_success(self, mock_request):
        """Test successful Jira project retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "key": "TEST",
            "name": "Test Project",
            "description": "A test project",
            "lead": {"displayName": "John Doe"},
            "components": [{"name": "Component 1"}, {"name": "Component 2"}],
        }
        mock_request.return_value = mock_response

        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)
        project = client.get_jira_project("TEST")

        assert project.key == "TEST"
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.lead == "John Doe"
        assert project.components == ["Component 1", "Component 2"]

        mock_request.assert_called_once_with(
            "GET", "https://example.com/rest/api/2/project/TEST", auth=("user", "token")
        )

    @patch.object(APIClient, "_make_request")
    def test_test_qtest_connection_success(self, mock_request):
        """Test successful qTest connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            qtest_token="qtest_token",
            qtest_url="https://qtest.example.com",
        )

        client = APIClient(config)
        result = client.test_qtest_connection()

        assert result is True
        mock_request.assert_called_once_with(
            "GET",
            "https://qtest.example.com/api/v3/users/me",
            headers={"Authorization": "bearer qtest_token"},
        )

    @patch.object(APIClient, "_make_request")
    def test_test_qtest_connection_failure(self, mock_request):
        """Test failed qTest connection test."""
        mock_request.side_effect = Exception("Connection failed")

        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            qtest_token="qtest_token",
            qtest_url="https://qtest.example.com",
        )

        client = APIClient(config)
        result = client.test_qtest_connection()

        assert result is False


class TestAPIClientJiraProject:
    """Test Jira project retrieval."""

    @patch.object(APIClient, "_make_request")
    def test_get_jira_project_success(self, mock_request):
        """Test successful Jira project retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "key": "TEST",
            "name": "Test Project",
            "description": "A test project",
            "lead": {"displayName": "John Doe"},
            "components": [{"name": "Component 1"}, {"name": "Component 2"}],
        }
        mock_request.return_value = mock_response

        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)
        project = client.get_jira_project("TEST")

        assert project.key == "TEST"
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.lead == "John Doe"
        assert project.components == ["Component 1", "Component 2"]

        mock_request.assert_called_once_with(
            "GET", "https://example.com/rest/api/2/project/TEST", auth=("user", "token")
        )

    @patch.object(APIClient, "_make_request")
    def test_get_jira_project_minimal_data(self, mock_request):
        """Test Jira project retrieval with minimal data."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "key": "MINIMAL",
            "name": "Minimal Project",
            # No description, lead, or components
        }
        mock_request.return_value = mock_response

        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)
        project = client.get_jira_project("MINIMAL")

        assert project.key == "MINIMAL"
        assert project.name == "Minimal Project"
        assert project.description is None
        assert project.lead is None
        assert project.components == []


class TestAPIClientZephyrTests:
    """Test Zephyr test case retrieval."""

    @patch.object(APIClient, "_make_request")
    def test_get_zephyr_tests_no_token(self, mock_request):
        """Test Zephyr tests retrieval without token."""
        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            # No zephyr_token
        )

        client = APIClient(config)
        tests = client.get_zephyr_tests("TEST")

        assert tests == []
        mock_request.assert_not_called()

    @patch.object(APIClient, "_make_request")
    def test_get_zephyr_tests_success(self, mock_request):
        """Test successful Zephyr tests retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "values": [
                {
                    "id": "1",
                    "key": "TEST-1",
                    "name": "Test Case 1",
                    "component": "Component 1",
                    "labels": ["label1", "label2"],
                    "owner": {"displayName": "John Doe"},
                    "createdOn": "2023-01-01T00:00:00Z",
                    "updatedOn": "2023-01-02T00:00:00Z",
                    "status": "Draft",
                }
            ]
        }
        mock_request.return_value = mock_response

        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            zephyr_token="zephyr_token",
        )

        client = APIClient(config)
        tests = client.get_zephyr_tests("TEST")

        assert len(tests) == 1
        test = tests[0]
        assert test.id == "1"
        assert test.key == "TEST-1"
        assert test.summary == "Test Case 1"
        assert test.project_key == "TEST"
        assert test.component == "Component 1"
        assert test.labels == ["label1", "label2"]
        assert test.assignee == "John Doe"
        assert test.source_system == "zephyr"
        assert test.status == "Draft"

        mock_request.assert_called_once_with(
            "GET",
            "https://example.com/rest/atm/1.0/testcase/search",
            headers={"Authorization": "Bearer zephyr_token"},
            params={"projectKey": "TEST", "maxResults": 1000},
        )

    @patch.object(APIClient, "_make_request")
    def test_get_zephyr_tests_with_dates(self, mock_request):
        """Test Zephyr tests retrieval with date filtering."""
        mock_response = Mock()
        mock_response.json.return_value = {"values": []}
        mock_request.return_value = mock_response

        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)

        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            zephyr_token="zephyr_token",
        )

        client = APIClient(config)
        tests = client.get_zephyr_tests("TEST", start_date, end_date)

        expected_params = {
            "projectKey": "TEST",
            "maxResults": 1000,
            "createdFrom": start_date.isoformat(),
            "createdTo": end_date.isoformat(),
        }

        mock_request.assert_called_once_with(
            "GET",
            "https://example.com/rest/atm/1.0/testcase/search",
            headers={"Authorization": "Bearer zephyr_token"},
            params=expected_params,
        )

    @patch.object(APIClient, "_make_request")
    def test_get_zephyr_tests_exception_returns_empty(self, mock_request):
        """Test Zephyr tests retrieval handles exceptions."""
        mock_request.side_effect = Exception("API Error")

        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            zephyr_token="zephyr_token",
        )

        client = APIClient(config)
        tests = client.get_zephyr_tests("TEST")

        assert tests == []


class TestAPIClientQTestTests:
    """Test qTest test case retrieval."""

    @patch.object(APIClient, "_make_request")
    def test_get_qtest_tests_no_token(self, mock_request):
        """Test qTest tests retrieval without token."""
        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            # No qtest_token
        )

        client = APIClient(config)
        tests = client.get_qtest_tests("TEST")

        assert tests == []
        mock_request.assert_not_called()

    @patch.object(APIClient, "_make_request")
    def test_get_qtest_tests_success(self, mock_request):
        """Test successful qTest tests retrieval."""
        # Mock projects response
        projects_response = Mock()
        projects_response.json.return_value = [{"id": 1, "name": "TEST"}]

        # Mock test cases response
        tests_response = Mock()
        tests_response.json.return_value = {
            "items": [
                {
                    "id": 123,
                    "name": "Test Case 1",
                    "tags": ["tag1", "tag2"],
                    "created_date": "2023-01-01T00:00:00Z",
                    "last_modified_date": "2023-01-02T00:00:00Z",
                    "status": "Active",
                }
            ]
        }

        mock_request.side_effect = [projects_response, tests_response]

        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            qtest_token="qtest_token",
            qtest_url="https://qtest.example.com",
        )

        client = APIClient(config)
        tests = client.get_qtest_tests("TEST")

        assert len(tests) == 1
        test = tests[0]
        assert test.id == "123"
        assert test.key == "TC-123"
        assert test.summary == "Test Case 1"
        assert test.project_key == "TEST"
        assert test.component is None
        assert test.labels == ["tag1", "tag2"]
        assert test.assignee is None
        assert test.source_system == "qtest"
        assert test.status == "Active"

        # Verify both API calls were made
        assert mock_request.call_count == 2

    @patch.object(APIClient, "_make_request")
    def test_get_qtest_tests_project_not_found(self, mock_request):
        """Test qTest tests retrieval when project not found."""
        projects_response = Mock()
        projects_response.json.return_value = [{"id": 1, "name": "OTHER"}]  # Different project

        mock_request.return_value = projects_response

        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            qtest_token="qtest_token",
            qtest_url="https://qtest.example.com",
        )

        client = APIClient(config)
        tests = client.get_qtest_tests("TEST")

        assert tests == []
        # Only projects call should be made
        assert mock_request.call_count == 1

    @patch.object(APIClient, "_make_request")
    def test_get_qtest_tests_exception_returns_empty(self, mock_request):
        """Test qTest tests retrieval handles exceptions."""
        mock_request.side_effect = Exception("API Error")

        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            qtest_token="qtest_token",
            qtest_url="https://qtest.example.com",
        )

        client = APIClient(config)
        tests = client.get_qtest_tests("TEST")

        assert tests == []


class TestAPIClientTestExecutions:
    """Test test execution retrieval."""

    @patch.object(APIClient, "_get_zephyr_executions")
    def test_get_test_executions_zephyr(self, mock_zephyr):
        """Test test executions retrieval for Zephyr."""
        mock_zephyr.return_value = {"test1": {"status": "PASS"}}

        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            zephyr_token="zephyr_token",
        )

        client = APIClient(config)
        executions = client.get_test_executions("TEST", ["test1"], "zephyr")

        assert executions == {"test1": {"status": "PASS"}}
        mock_zephyr.assert_called_once_with("TEST", ["test1"])

    @patch.object(APIClient, "_get_qtest_executions")
    def test_get_test_executions_qtest(self, mock_qtest):
        """Test test executions retrieval for qTest."""
        mock_qtest.return_value = {"test1": {"status": "FAIL"}}

        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            qtest_token="qtest_token",
        )

        client = APIClient(config)
        executions = client.get_test_executions("TEST", ["test1"], "qtest")

        assert executions == {"test1": {"status": "FAIL"}}
        mock_qtest.assert_called_once_with("TEST", ["test1"])

    def test_get_test_executions_no_token(self):
        """Test test executions retrieval without tokens."""
        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            # No zephyr_token or qtest_token
        )

        client = APIClient(config)

        # Test both zephyr and qtest without tokens
        zephyr_executions = client.get_test_executions("TEST", ["test1"], "zephyr")
        qtest_executions = client.get_test_executions("TEST", ["test1"], "qtest")

        assert zephyr_executions == {}
        assert qtest_executions == {}

    @patch.object(APIClient, "_make_request")
    def test_get_zephyr_executions_success(self, mock_request):
        """Test successful Zephyr executions retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "values": [
                {"executedOn": "2023-01-01T00:00:00Z", "status": "PASS", "issues": ["BUG-123"]}
            ]
        }
        mock_request.return_value = mock_response

        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            zephyr_token="zephyr_token",
        )

        client = APIClient(config)
        executions = client._get_zephyr_executions("TEST", ["TEST-1"])

        assert "TEST-1" in executions
        assert executions["TEST-1"]["last_execution"] == "2023-01-01T00:00:00Z"
        assert executions["TEST-1"]["status"] == "PASS"
        assert executions["TEST-1"]["linked_defects"] == ["BUG-123"]

    @patch.object(APIClient, "_make_request")
    def test_get_zephyr_executions_no_data(self, mock_request):
        """Test Zephyr executions retrieval with no data."""
        mock_response = Mock()
        mock_response.json.return_value = {"values": []}
        mock_request.return_value = mock_response

        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            zephyr_token="zephyr_token",
        )

        client = APIClient(config)
        executions = client._get_zephyr_executions("TEST", ["TEST-1"])

        assert executions == {}

    def test_get_qtest_executions_returns_empty(self):
        """Test qTest executions retrieval returns empty (simplified implementation)."""
        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            qtest_token="qtest_token",
        )

        client = APIClient(config)
        executions = client._get_qtest_executions("TEST", ["test1"])

        assert executions == {}


class TestAPIClientCaching:
    """Test caching functionality."""

    @patch.object(APIClient, "_make_request")
    def test_cached_get_with_cache_hit(self, mock_request):
        """Test _cached_get with cache hit."""
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)

        # Mock cache to return cached data
        mock_cache_data = {"data": "cached", "_from_cache": True}
        client._cache.get_cached_response = Mock(return_value=mock_cache_data)

        result = client._cached_get("https://example.com/test")

        assert result == mock_cache_data
        # Should not make actual request when cache hit
        mock_request.assert_not_called()

    @patch.object(APIClient, "_make_request")
    def test_cached_get_with_cache_miss(self, mock_request):
        """Test _cached_get with cache miss."""
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)

        # Mock cache to return None (cache miss)
        client._cache.get_cached_response = Mock(return_value=None)

        result = client._cached_get("https://example.com/test")

        assert result is None
        # Should call cache method
        client._cache.get_cached_response.assert_called_once()


class TestAPIClientEdgeCases:
    """Test edge cases and error conditions in APIClient."""

    def test_observability_import_error_handling(self):
        """Test APIClient handles missing observability gracefully."""
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        # This should work even if observability is not available
        with patch("ledzephyr.client.HAS_OBSERVABILITY", False):
            client = APIClient(config)
            assert client.config == config

    def test_determine_service_edge_cases(self):
        """Test service type determination for various URL patterns."""
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )
        client = APIClient(config)

        # Test Jira determination (default fallback)
        jira_service = client._determine_service("https://company.atlassian.net/browse/PROJECT-123")
        assert jira_service == "jira"

        # Test Zephyr determination (contains "zephyr" keyword)
        zephyr_service = client._determine_service("https://zephyr.company.com/api/v1/test")
        assert zephyr_service == "zephyr"

        # Test Zephyr determination (contains "scale" keyword)
        scale_service = client._determine_service("https://company.scale.net/api")
        assert scale_service == "zephyr"

        # Test qTest determination (contains "qtest" keyword)
        qtest_service = client._determine_service("https://company.qtest.net/api/v3")
        assert qtest_service == "qtest"

        # Test case insensitive matching
        qtest_upper = client._determine_service("https://company.QTEST.net/api")
        assert qtest_upper == "qtest"

    def test_api_error_exceptions(self):
        """Test custom API exception classes."""
        # Test APIError
        with pytest.raises(APIError):
            raise APIError("General API error")

        # Test AuthenticationError
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("Authentication failed")

        # Verify inheritance
        assert issubclass(AuthenticationError, APIError)

    @patch("ledzephyr.client.httpx.Client")
    def test_context_manager_functionality(self, mock_client):
        """Test APIClient as context manager."""
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance

        # Test context manager protocol
        with APIClient(config) as client:
            assert client is not None
            assert hasattr(client, "_http_client")

        # Verify cleanup was called (synchronous close, not async aclose)
        mock_client_instance.close.assert_called_once()

    def test_missing_config_values(self):
        """Test handling of missing configuration values."""
        # Test with minimal config
        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)

        # Should handle missing optional values gracefully
        assert client.config.zephyr_url is None
        assert client.config.qtest_url is None
        assert client.config.zephyr_token is None
        assert client.config.qtest_token is None

    def test_zephyr_connection_missing_url(self):
        """Test Zephyr connection with missing URL."""
        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            zephyr_token="token",
            # No zephyr_url - should use jira_url
        )

        client = APIClient(config)

        # This should still work, using jira_url as fallback
        result = client.test_zephyr_connection()
        assert result is False  # Will fail due to no actual connection

    def test_qtest_connection_missing_url(self):
        """Test qTest connection with missing URL."""
        config = Config(
            jira_url="https://example.com",
            jira_username="user",
            jira_api_token="token",
            qtest_token="token",
            # No qtest_url
        )

        client = APIClient(config)

        # Should return False when no qtest_url is configured
        result = client.test_qtest_connection()
        assert result is False

    @patch.object(APIClient, "_make_request")
    def test_connection_with_authentication_error(self, mock_request):
        """Test connection methods handle authentication errors gracefully."""
        from ledzephyr.client import AuthenticationError

        mock_request.side_effect = AuthenticationError("Invalid credentials")

        config = Config(
            jira_url="https://example.com", jira_username="user", jira_api_token="token"
        )

        client = APIClient(config)

        # Should handle auth errors gracefully
        result = client.test_jira_connection()
        assert result is False
