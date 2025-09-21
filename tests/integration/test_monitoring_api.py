"""Integration tests for monitoring API endpoints."""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from ledzephyr.monitoring_api import app
from ledzephyr.observability import HealthStatus


@pytest.fixture
def test_client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_observability():
    """Mock observability for tests."""
    with patch("ledzephyr.monitoring_api.init_observability") as mock_init:
        mock_obs = Mock()
        mock_obs.check_health.return_value = {
            "database": HealthStatus(
                name="database",
                status="healthy",
                message="Database connection OK",
                metadata={"connections": 5},
            ),
            "api": HealthStatus(
                name="api",
                status="healthy",
                message="External APIs reachable",
            ),
            "cache": HealthStatus(
                name="cache",
                status="healthy",
                message="Cache operational",
            ),
        }
        mock_obs.get_metrics_dump.return_value = (
            b"# HELP test_metric Test metric\n# TYPE test_metric counter\ntest_metric 1.0\n"
        )
        mock_init.return_value = mock_obs

        with patch("ledzephyr.monitoring_api.get_observability") as mock_get:
            mock_get.return_value = mock_obs
            yield mock_obs


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_endpoint_all_healthy(self, test_client, mock_observability):
        """Test /health endpoint when all services are healthy."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "checks" in data

        # Verify individual checks
        assert data["checks"]["database"]["status"] == "healthy"
        assert data["checks"]["api"]["status"] == "healthy"
        assert data["checks"]["cache"]["status"] == "healthy"

    def test_health_endpoint_degraded(self, test_client, mock_observability):
        """Test /health endpoint when services are degraded."""
        mock_observability.check_health.return_value = {
            "database": HealthStatus(
                name="database",
                status="healthy",
                message="Database connection OK",
            ),
            "api": HealthStatus(
                name="api",
                status="degraded",
                message="High latency detected",
            ),
            "cache": HealthStatus(
                name="cache",
                status="healthy",
                message="Cache operational",
            ),
        }

        response = test_client.get("/health")

        assert response.status_code == 207  # Multi-status
        data = response.json()
        assert data["status"] == "degraded"

    def test_health_endpoint_unhealthy(self, test_client, mock_observability):
        """Test /health endpoint when services are unhealthy."""
        mock_observability.check_health.return_value = {
            "database": HealthStatus(
                name="database",
                status="unhealthy",
                message="Connection failed",
            ),
            "api": HealthStatus(
                name="api",
                status="healthy",
                message="APIs reachable",
            ),
            "cache": HealthStatus(
                name="cache",
                status="degraded",
                message="High miss rate",
            ),
        }

        response = test_client.get("/health")

        assert response.status_code == 503  # Service unavailable
        data = response.json()
        assert data["status"] == "unhealthy"

    def test_liveness_probe(self, test_client):
        """Test /health/live endpoint."""
        response = test_client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data

    def test_readiness_probe_ready(self, test_client, mock_observability):
        """Test /health/ready endpoint when service is ready."""
        response = test_client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "timestamp" in data

    def test_readiness_probe_not_ready(self, test_client, mock_observability):
        """Test /health/ready endpoint when service is not ready."""
        mock_observability.check_health.return_value = {
            "database": HealthStatus(
                name="database",
                status="unhealthy",
                message="Connection failed",
            ),
            "api": HealthStatus(
                name="api",
                status="healthy",
                message="APIs reachable",
            ),
        }

        response = test_client.get("/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert "reason" in data


class TestMetricsEndpoint:
    """Test metrics endpoint."""

    def test_metrics_endpoint(self, test_client, mock_observability):
        """Test /metrics endpoint returns Prometheus metrics."""
        response = test_client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

        content = response.text
        assert "# HELP" in content
        assert "# TYPE" in content
        assert "test_metric" in content

    def test_metrics_format(self, test_client, mock_observability):
        """Test metrics are in correct Prometheus format."""
        # Mock more realistic metrics
        metrics_text = """# HELP ledzephyr_api_requests_total Total API requests
# TYPE ledzephyr_api_requests_total counter
ledzephyr_api_requests_total{method="GET",endpoint="test",status="200"} 42.0
# HELP ledzephyr_api_request_duration_seconds API request duration
# TYPE ledzephyr_api_request_duration_seconds histogram
ledzephyr_api_request_duration_seconds_bucket{method="GET",endpoint="test",le="0.1"} 10.0
ledzephyr_api_request_duration_seconds_bucket{method="GET",endpoint="test",le="0.5"} 35.0
ledzephyr_api_request_duration_seconds_bucket{method="GET",endpoint="test",le="1.0"} 40.0
ledzephyr_api_request_duration_seconds_bucket{method="GET",endpoint="test",le="+Inf"} 42.0
ledzephyr_api_request_duration_seconds_sum{method="GET",endpoint="test"} 15.5
ledzephyr_api_request_duration_seconds_count{method="GET",endpoint="test"} 42.0
"""
        mock_observability.get_metrics_dump.return_value = metrics_text.encode()

        response = test_client.get("/metrics")

        assert response.status_code == 200
        content = response.text

        # Verify metric components
        assert "ledzephyr_api_requests_total" in content
        assert "counter" in content
        assert "histogram" in content
        assert "_bucket" in content
        assert "_sum" in content
        assert "_count" in content


class TestInfoEndpoint:
    """Test service info endpoint."""

    def test_info_endpoint(self, test_client):
        """Test /info endpoint returns service information."""
        response = test_client.get("/info")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "ledzephyr"
        assert "version" in data
        assert "python_version" in data
        assert "platform" in data
        assert "hostname" in data
        assert "working_directory" in data
        assert "timestamp" in data


class TestDebugEndpoints:
    """Test debug endpoints."""

    def test_debug_config_development(self, test_client):
        """Test /debug/config endpoint in development environment."""
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            with patch("ledzephyr.monitoring_api.Config") as mock_config:
                mock_config.from_env.return_value = Mock(
                    jira_url="https://test.atlassian.net",
                    jira_username="test@example.com",
                    jira_api_token="secret-token",
                    zephyr_token="zephyr-secret",
                    qtest_token="qtest-secret",
                )

                response = test_client.get("/debug/config")

                assert response.status_code == 200
                data = response.json()

                # Verify sensitive values are redacted
                assert data.get("jira_api_token") == "***REDACTED***"
                assert data.get("zephyr_token") == "***REDACTED***"
                assert data.get("qtest_token") == "***REDACTED***"

                # Non-sensitive values should be present
                assert "jira_url" in data

    def test_debug_config_production(self, test_client):
        """Test /debug/config endpoint is disabled in production."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            response = test_client.get("/debug/config")

            assert response.status_code == 403
            data = response.json()
            assert "disabled in production" in data["error"]

    def test_debug_config_error_handling(self, test_client):
        """Test /debug/config handles configuration errors."""
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            with patch("ledzephyr.monitoring_api.Config") as mock_config:
                mock_config.from_env.side_effect = Exception("Config error")

                response = test_client.get("/debug/config")

                assert response.status_code == 200
                data = response.json()
                assert "error" in data
                assert "Config error" in data["error"]

    def test_debug_stats_development(self, test_client):
        """Test /debug/stats endpoint in development."""
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            response = test_client.get("/debug/stats")

            assert response.status_code == 200
            data = response.json()

            assert "memory" in data
            assert "cpu" in data
            assert "gc" in data
            assert "timestamp" in data

            # Memory stats
            assert "rss_mb" in data["memory"]
            assert "vms_mb" in data["memory"]
            assert "percent" in data["memory"]

            # CPU stats
            assert "percent" in data["cpu"]
            assert "num_threads" in data["cpu"]

            # GC stats
            assert "collections" in data["gc"]
            assert "objects" in data["gc"]

    def test_debug_stats_production(self, test_client):
        """Test /debug/stats endpoint is disabled in production."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            response = test_client.get("/debug/stats")

            assert response.status_code == 403
            data = response.json()
            assert "disabled in production" in data["error"]


class TestCORSHeaders:
    """Test CORS configuration."""

    def test_cors_headers_present(self, test_client):
        """Test that CORS headers are present."""
        response = test_client.get("/health")

        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "*"

    def test_cors_preflight(self, test_client):
        """Test CORS preflight request."""
        response = test_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert "access-control-allow-methods" in response.headers


class TestErrorHandling:
    """Test error handling in monitoring API."""

    def test_health_check_exception_handling(self, test_client, mock_observability):
        """Test health endpoint handles check exceptions gracefully."""

        # Mock a check that raises an exception
        def failing_check():
            raise Exception("Check failed")

        mock_observability.check_health.side_effect = Exception("All checks failed")

        response = test_client.get("/health")

        # Should still return a response, not 500
        assert response.status_code in [200, 503]

    def test_metrics_exception_handling(self, test_client, mock_observability):
        """Test metrics endpoint handles exceptions gracefully."""
        mock_observability.get_metrics_dump.side_effect = Exception("Metrics error")

        response = test_client.get("/metrics")

        # Should handle the error gracefully
        assert response.status_code == 500


class TestStartupShutdown:
    """Test application startup and shutdown events."""

    def test_startup_event(self):
        """Test startup event initializes observability."""
        with patch("ledzephyr.monitoring_api.init_observability") as mock_init:
            mock_obs = Mock()
            mock_init.return_value = mock_obs

            # Trigger startup event
            with TestClient(app) as client:
                # Startup should have been called
                mock_init.assert_called_once()

                # Health checks should be registered
                assert mock_obs.register_health_check.call_count >= 3

    def test_health_check_registration(self):
        """Test that health checks are properly registered on startup."""
        with patch("ledzephyr.monitoring_api.init_observability") as mock_init:
            mock_obs = Mock()
            mock_init.return_value = mock_obs

            with TestClient(app):
                # Verify specific health checks were registered
                calls = mock_obs.register_health_check.call_args_list
                registered_names = [call[0][0] for call in calls]

                assert "database" in registered_names
                assert "api" in registered_names
                assert "cache" in registered_names


@pytest.mark.asyncio
class TestAsyncEndpoints:
    """Test async behavior of endpoints."""

    async def test_concurrent_health_checks(self, test_client):
        """Test that health checks can handle concurrent requests."""
        import asyncio

        async def make_request():
            return test_client.get("/health")

        # Make multiple concurrent requests
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*[asyncio.create_task(t) for t in tasks])

        # All should succeed
        for response in responses:
            assert response.status_code in [200, 207, 503]

    async def test_metrics_under_load(self, test_client):
        """Test metrics endpoint under concurrent load."""
        import asyncio

        async def make_request():
            return test_client.get("/metrics")

        # Make multiple concurrent requests
        tasks = [make_request() for _ in range(20)]
        responses = await asyncio.gather(*[asyncio.create_task(t) for t in tasks])

        # All should return metrics
        for response in responses:
            assert response.status_code == 200
            assert "# HELP" in response.text
