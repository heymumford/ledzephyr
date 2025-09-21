"""Integration tests for pull layer using API stubs."""

from unittest.mock import Mock, patch

import pytest
from tests.integration.doubles.stub_jira import JiraAPIStub, QTestAPIStub, ZephyrAPIStub

from ledzephyr.client import APIClient
from ledzephyr.config import Config


class TestPullWithStubs:
    """Integration tests using API stubs."""

    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return Config(
            jira_url="https://test.atlassian.net",
            jira_username="test@example.com",
            jira_api_token="test_token",
            zephyr_token="zephyr_test_token",
            qtest_url="https://test.qtestnet.com",
            qtest_token="qtest_test_token",
            timeout=30,
            max_retries=3,
        )

    @pytest.fixture
    def jira_stub(self):
        """Create Jira API stub."""
        return JiraAPIStub(preset="basic_project")

    @pytest.fixture
    def zephyr_stub(self):
        """Create Zephyr API stub."""
        return ZephyrAPIStub(preset="mixed_execution_status")

    @pytest.fixture
    def qtest_stub(self):
        """Create qTest API stub."""
        return QTestAPIStub(preset="basic_tests")

    def test_jira_connection_with_stub(self, test_config, jira_stub):
        """Test Jira connection using stub."""
        client = APIClient(test_config)

        # Mock the HTTP request to use our stub
        with patch.object(client, "_make_request") as mock_request:
            # Simulate successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = jira_stub.get_myself()
            mock_request.return_value = mock_response

            # Test connection
            result = client.test_jira_connection()

            assert result is True
            mock_request.assert_called_once()

            # Verify stub logged the call
            calls = jira_stub.get_call_log()
            assert len(calls) == 1
            assert calls[0]["url"] == "/rest/api/2/myself"

    def test_get_jira_project_with_stub(self, test_config, jira_stub):
        """Test getting Jira project information using stub."""
        client = APIClient(test_config)

        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = jira_stub.get_project("DEMO")
            mock_request.return_value = mock_response

            # Get project
            project = client.get_jira_project("DEMO")

            assert project.key == "DEMO"
            assert project.name == "Demo Project"
            assert "Frontend" in project.components
            assert "Backend" in project.components

            # Verify stub logged the call
            calls = jira_stub.get_call_log()
            assert len(calls) == 1
            assert "DEMO" in calls[0]["url"]

    def test_zephyr_connection_with_stub(self, test_config, zephyr_stub):
        """Test Zephyr connection using stub."""
        client = APIClient(test_config)

        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = zephyr_stub.health_check()
            mock_request.return_value = mock_response

            result = client.test_zephyr_connection()

            assert result is True

            # Verify stub logged the call
            calls = zephyr_stub.get_call_log()
            assert len(calls) == 1
            assert calls[0]["url"] == "/rest/atm/1.0/healthcheck"

    def test_get_zephyr_tests_with_stub(self, test_config, zephyr_stub):
        """Test getting Zephyr tests using stub."""
        client = APIClient(test_config)

        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = zephyr_stub.search_test_cases("DEMO")
            mock_request.return_value = mock_response

            tests = client.get_zephyr_tests("DEMO")

            assert len(tests) == 2
            assert tests[0].key == "Z-1"
            assert tests[0].summary == "User login test"
            assert tests[0].component == "Frontend"
            assert tests[1].key == "Z-2"

            # Verify stub logged the call
            calls = zephyr_stub.get_call_log()
            assert len(calls) == 1
            assert "testcase/search" in calls[0]["url"]

    def test_qtest_connection_with_stub(self, test_config, qtest_stub):
        """Test qTest connection using stub."""
        client = APIClient(test_config)

        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = qtest_stub.get_user()
            mock_request.return_value = mock_response

            result = client.test_qtest_connection()

            assert result is True

            # Verify stub logged the call
            calls = qtest_stub.get_call_log()
            assert len(calls) == 1
            assert calls[0]["url"] == "/api/v3/users/me"

    def test_get_qtest_tests_with_stub(self, test_config, qtest_stub):
        """Test getting qTest tests using stub."""
        client = APIClient(test_config)

        with patch.object(client, "_make_request") as mock_request:
            # Mock the projects call first
            projects_response = Mock()
            projects_response.json.return_value = qtest_stub.get_projects()

            # Mock the test cases call
            test_cases_response = Mock()
            test_cases_response.json.return_value = qtest_stub.get_test_cases(12345)

            # Return different responses based on URL
            def mock_request_side_effect(*args, **kwargs):
                url = args[1] if len(args) > 1 else kwargs.get("url", "")
                if "/projects" in url and "/test-cases" not in url:
                    return projects_response
                else:
                    return test_cases_response

            mock_request.side_effect = mock_request_side_effect

            tests = client.get_qtest_tests("DEMO")

            assert len(tests) == 2
            assert tests[0].key == "TC-1001"
            assert tests[0].summary == "User registration flow"
            assert tests[1].key == "TC-1002"

            # Verify stub logged both calls
            calls = qtest_stub.get_call_log()
            assert len(calls) == 2
            assert any("projects" in call["url"] for call in calls)
            assert any("test-cases" in call["url"] for call in calls)


class TestAPISpying:
    """Test API call tracking and assertions."""

    def test_api_call_headers_and_auth(self, test_config):
        """Test that proper headers and auth are used in API calls."""
        client = APIClient(test_config)
        jira_stub = JiraAPIStub()

        captured_requests = []

        def capture_request(*args, **kwargs):
            captured_requests.append(
                {
                    "method": args[0],
                    "url": args[1],
                    "auth": kwargs.get("auth"),
                    "headers": kwargs.get("headers", {}),
                }
            )
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = jira_stub.get_myself()
            return mock_response

        with patch.object(client, "_make_request", side_effect=capture_request):
            client.test_jira_connection()

        # Verify authentication was used
        assert len(captured_requests) == 1
        request = captured_requests[0]
        assert request["auth"] == (test_config.jira_username, test_config.jira_api_token)
        assert request["headers"]["Accept"] == "application/json"

    def test_pagination_usage_tracking(self, test_config):
        """Test that pagination parameters are properly tracked."""
        client = APIClient(test_config)
        zephyr_stub = ZephyrAPIStub()

        captured_requests = []

        def capture_request(*args, **kwargs):
            captured_requests.append(
                {"method": args[0], "url": args[1], "params": kwargs.get("params", {})}
            )
            mock_response = Mock()
            mock_response.json.return_value = zephyr_stub.search_test_cases("DEMO")
            return mock_response

        with patch.object(client, "_make_request", side_effect=capture_request):
            client.get_zephyr_tests("DEMO")

        # Verify pagination parameters
        assert len(captured_requests) == 1
        request = captured_requests[0]
        assert "projectKey" in request["params"]
        assert request["params"]["projectKey"] == "DEMO"
        assert "maxResults" in request["params"]
        assert request["params"]["maxResults"] == 1000

    def test_multiple_source_coordination(self, test_config):
        """Test that calls to multiple API sources are properly coordinated."""
        from ledzephyr.metrics import MetricsCalculator

        client = APIClient(test_config)
        calculator = MetricsCalculator(client)

        # Track all API calls
        all_calls = []

        def track_calls(*args, **kwargs):
            all_calls.append(
                {
                    "url": args[1] if len(args) > 1 else kwargs.get("url", ""),
                    "timestamp": len(all_calls),  # Simple ordering
                }
            )
            mock_response = Mock()
            mock_response.status_code = 200

            # Return appropriate response based on URL
            if "project" in args[1]:
                mock_response.json.return_value = {
                    "key": "DEMO",
                    "name": "Demo Project",
                    "components": [],
                }
            elif "testcase/search" in args[1]:
                mock_response.json.return_value = {"values": []}
            elif "projects" in args[1]:
                mock_response.json.return_value = []
            else:
                mock_response.json.return_value = {}

            return mock_response

        with patch.object(client, "_make_request", side_effect=track_calls):
            try:
                calculator.calculate_metrics("DEMO", "7d")
            except Exception:
                # Expected since we're using minimal stubs
                pass

        # Verify the sequence of calls
        assert len(all_calls) >= 2  # At least Jira project + one test source
        urls = [call["url"] for call in all_calls]
        assert any("project" in url for url in urls)  # Jira project call
        assert any("testcase" in url or "projects" in url for url in urls)  # Test source calls
