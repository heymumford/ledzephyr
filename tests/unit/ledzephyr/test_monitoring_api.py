"""
Unit tests for monitoring_api module.

Tests health check endpoints, metrics collection, and monitoring functionality
using TDD methodology with comprehensive mocking of external dependencies.
"""

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ledzephyr.monitoring_api import app
from ledzephyr.observability import HealthStatus


@pytest.fixture
def client():
    """Create test client for the monitoring API."""
    return TestClient(app)


@pytest.fixture
def mock_observability():
    """Mock observability manager."""
    with patch("ledzephyr.monitoring_api.get_observability") as mock:
        obs_manager = MagicMock()
        mock.return_value = obs_manager
        yield obs_manager


@pytest.fixture
def mock_init_observability():
    """Mock observability initialization."""
    with patch("ledzephyr.monitoring_api.init_observability") as mock:
        obs_manager = MagicMock()
        mock.return_value = obs_manager
        yield obs_manager


class TestHealthCheckEndpoint:
    """Test the main health check endpoint."""

    def test_health_check_all_healthy_returns_200(self, client, mock_observability):
        """Test health check returns 200 when all components are healthy."""
        # Arrange
        mock_observability.check_health.return_value = {
            "database": HealthStatus(
                name="database",
                status="healthy",
                message="Database connection OK",
                metadata={"connection_pool_size": 10},
                last_check=datetime(2023, 1, 1, 12, 0, 0),
            ),
            "api": HealthStatus(
                name="api",
                status="healthy",
                message="API endpoints responding",
                metadata={"response_time_ms": 150},
                last_check=datetime(2023, 1, 1, 12, 0, 0),
            ),
        }

        # Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "checks" in data
        assert len(data["checks"]) == 2
        assert data["checks"]["database"]["status"] == "healthy"
        assert data["checks"]["api"]["status"] == "healthy"

    def test_health_check_with_degraded_returns_207(self, client, mock_observability):
        """Test health check returns 207 when some components are degraded."""
        # Arrange
        mock_observability.check_health.return_value = {
            "database": HealthStatus(
                name="database",
                status="healthy",
                message="Database connection OK",
                last_check=datetime(2023, 1, 1, 12, 0, 0),
            ),
            "cache": HealthStatus(
                name="cache",
                status="degraded",
                message="Cache hit rate below threshold",
                last_check=datetime(2023, 1, 1, 12, 0, 0),
            ),
        }

        # Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 207
        data = response.json()
        assert data["status"] == "degraded"

    def test_health_check_with_unhealthy_returns_503(self, client, mock_observability):
        """Test health check returns 503 when any component is unhealthy."""
        # Arrange
        mock_observability.check_health.return_value = {
            "database": HealthStatus(
                name="database",
                status="unhealthy",
                message="Database connection failed",
                last_check=datetime(2023, 1, 1, 12, 0, 0),
            ),
            "api": HealthStatus(
                name="api",
                status="healthy",
                message="API endpoints responding",
                last_check=datetime(2023, 1, 1, 12, 0, 0),
            ),
        }

        # Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"

    def test_health_check_includes_metadata(self, client, mock_observability):
        """Test health check includes component metadata."""
        # Arrange
        mock_observability.check_health.return_value = {
            "database": HealthStatus(
                name="database",
                status="healthy",
                message="Database connection OK",
                metadata={"connection_pool_size": 10, "active_connections": 2},
                last_check=datetime(2023, 1, 1, 12, 0, 0),
            ),
        }

        # Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        db_check = data["checks"]["database"]
        assert db_check["metadata"]["connection_pool_size"] == 10
        assert db_check["metadata"]["active_connections"] == 2


class TestLivenessProbe:
    """Test the Kubernetes liveness probe endpoint."""

    def test_liveness_probe_returns_alive_status(self, client):
        """Test liveness probe returns alive status."""
        # Act
        response = client.get("/health/live")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data

    def test_liveness_probe_timestamp_format(self, client):
        """Test liveness probe timestamp is in ISO format."""
        # Act
        response = client.get("/health/live")

        # Assert
        data = response.json()
        # Should parse without error
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))


class TestReadinessProbe:
    """Test the Kubernetes readiness probe endpoint."""

    def test_readiness_probe_ready_when_critical_healthy(self, client, mock_observability):
        """Test readiness probe returns ready when critical components are healthy."""
        # Arrange
        mock_observability.check_health.return_value = {
            "database": HealthStatus(
                name="database",
                status="healthy",
                message="Database connection OK",
                last_check=datetime(2023, 1, 1, 12, 0, 0),
            ),
            "api": HealthStatus(
                name="api",
                status="healthy",
                message="API endpoints responding",
                last_check=datetime(2023, 1, 1, 12, 0, 0),
            ),
            "cache": HealthStatus(
                name="cache",
                status="degraded",
                message="Cache degraded but not critical",
                last_check=datetime(2023, 1, 1, 12, 0, 0),
            ),
        }

        # Act
        response = client.get("/health/ready")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_readiness_probe_not_ready_when_database_unhealthy(self, client, mock_observability):
        """Test readiness probe returns not ready when database is unhealthy."""
        # Arrange
        mock_observability.check_health.return_value = {
            "database": HealthStatus(
                name="database",
                status="unhealthy",
                message="Database connection failed",
                last_check=datetime(2023, 1, 1, 12, 0, 0),
            ),
            "api": HealthStatus(
                name="api",
                status="healthy",
                message="API endpoints responding",
                last_check=datetime(2023, 1, 1, 12, 0, 0),
            ),
        }

        # Act
        response = client.get("/health/ready")

        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert "database is unhealthy" in data["reason"]

    def test_readiness_probe_not_ready_when_api_unhealthy(self, client, mock_observability):
        """Test readiness probe returns not ready when API is unhealthy."""
        # Arrange
        mock_observability.check_health.return_value = {
            "database": HealthStatus(
                name="database",
                status="healthy",
                message="Database connection OK",
                last_check=datetime(2023, 1, 1, 12, 0, 0),
            ),
            "api": HealthStatus(
                name="api",
                status="unhealthy",
                message="API endpoints not responding",
                last_check=datetime(2023, 1, 1, 12, 0, 0),
            ),
        }

        # Act
        response = client.get("/health/ready")

        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert "api is unhealthy" in data["reason"]

    def test_readiness_probe_ready_when_non_critical_missing(self, client, mock_observability):
        """Test readiness probe is ready even when non-critical components are missing."""
        # Arrange
        mock_observability.check_health.return_value = {
            "database": HealthStatus(
                name="database",
                status="healthy",
                message="Database connection OK",
                last_check=datetime(2023, 1, 1, 12, 0, 0),
            ),
            "api": HealthStatus(
                name="api",
                status="healthy",
                message="API endpoints responding",
                last_check=datetime(2023, 1, 1, 12, 0, 0),
            ),
            # cache not included - non-critical
        }

        # Act
        response = client.get("/health/ready")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


class TestMetricsEndpoint:
    """Test the Prometheus metrics endpoint."""

    def test_metrics_endpoint_returns_prometheus_format(self, client, mock_observability):
        """Test metrics endpoint returns data in Prometheus text format."""
        # Arrange
        metrics_data = (
            "# HELP ledzephyr_api_requests_total Total API requests\n"
            "# TYPE ledzephyr_api_requests_total counter\n"
            'ledzephyr_api_requests_total{method="GET",endpoint="/health",status="200"} 5.0\n'
        )
        mock_observability.get_metrics_dump.return_value = metrics_data.encode()

        # Act
        response = client.get("/metrics")

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
        assert "ledzephyr_api_requests_total" in response.text

    def test_metrics_endpoint_calls_observability(self, client, mock_observability):
        """Test metrics endpoint calls observability manager."""
        # Arrange
        mock_observability.get_metrics_dump.return_value = b"test_metrics"

        # Act
        client.get("/metrics")

        # Assert
        mock_observability.get_metrics_dump.assert_called_once()


class TestServiceInfoEndpoint:
    """Test the service information endpoint."""

    def test_service_info_includes_required_fields(self, client):
        """Test service info endpoint includes all required fields."""
        # Act
        response = client.get("/info")

        # Assert
        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "service",
            "version",
            "python_version",
            "platform",
            "processor",
            "hostname",
            "working_directory",
            "timestamp",
        ]

        for field in required_fields:
            assert field in data

    def test_service_info_has_correct_service_name(self, client):
        """Test service info returns correct service name."""
        # Act
        response = client.get("/info")

        # Assert
        data = response.json()
        assert data["service"] == "ledzephyr"

    @patch("platform.platform")
    @patch("platform.processor")
    @patch("platform.node")
    def test_service_info_uses_platform_data(
        self, mock_node, mock_processor, mock_platform, client
    ):
        """Test service info uses actual platform data."""
        # Arrange
        mock_platform.return_value = "Linux-5.4.0"
        mock_processor.return_value = "x86_64"
        mock_node.return_value = "test-host"

        # Act
        response = client.get("/info")

        # Assert
        data = response.json()
        assert data["platform"] == "Linux-5.4.0"
        assert data["processor"] == "x86_64"
        assert data["hostname"] == "test-host"


class TestDebugConfigEndpoint:
    """Test the debug configuration endpoint."""

    @patch.dict(os.environ, {"ENVIRONMENT": "development"})
    @patch("ledzephyr.config.Config.from_env")
    def test_debug_config_returns_config_in_development(self, mock_config, client):
        """Test debug config endpoint returns configuration in development."""
        # Arrange
        mock_config_obj = MagicMock()
        mock_config_obj.model_dump.return_value = {
            "jira_url": "https://test.atlassian.net",
            "jira_api_token": "secret_token",
            "zephyr_token": "secret_zephyr",
            "qtest_token": "secret_qtest",
            "timeout": 30,
        }
        mock_config.return_value = mock_config_obj

        # Act
        response = client.get("/debug/config")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["jira_url"] == "https://test.atlassian.net"
        assert data["jira_api_token"] == "***REDACTED***"
        assert data["zephyr_token"] == "***REDACTED***"
        assert data["qtest_token"] == "***REDACTED***"
        assert data["timeout"] == 30

    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_debug_config_forbidden_in_production(self, client):
        """Test debug config endpoint returns 403 in production."""
        # Act
        response = client.get("/debug/config")

        # Assert
        assert response.status_code == 403
        data = response.json()
        assert "Debug endpoints disabled in production" in data["error"]

    @patch.dict(os.environ, {"ENVIRONMENT": "development"})
    @patch("ledzephyr.config.Config.from_env")
    def test_debug_config_handles_config_error(self, mock_config, client):
        """Test debug config endpoint handles configuration errors."""
        # Arrange
        mock_config.side_effect = Exception("Config loading failed")

        # Act
        response = client.get("/debug/config")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "Could not load config" in data["error"]
        assert "Config loading failed" in data["error"]

    @patch.dict(os.environ, {}, clear=True)  # Clear ENVIRONMENT var
    @patch("ledzephyr.config.Config.from_env")
    def test_debug_config_defaults_to_development(self, mock_config, client):
        """Test debug config endpoint defaults to development when ENVIRONMENT is not set."""
        # Arrange
        mock_config_obj = MagicMock()
        mock_config_obj.model_dump.return_value = {"setting": "value"}
        mock_config.return_value = mock_config_obj

        # Act
        response = client.get("/debug/config")

        # Assert
        assert response.status_code == 200


class TestDebugStatsEndpoint:
    """Test the debug statistics endpoint."""

    @patch.dict(os.environ, {"ENVIRONMENT": "development"})
    @patch("psutil.Process")
    @patch("gc.get_count")
    @patch("gc.get_objects")
    def test_debug_stats_returns_system_metrics(
        self, mock_get_objects, mock_get_count, mock_process_class, client
    ):
        """Test debug stats endpoint returns system metrics in development."""
        # Arrange
        mock_process = MagicMock()
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 104857600  # 100MB in bytes
        mock_memory_info.vms = 209715200  # 200MB in bytes
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.memory_percent.return_value = 5.5
        mock_process.cpu_percent.return_value = 15.2
        mock_process.num_threads.return_value = 8
        mock_process.connections.return_value = ["conn1", "conn2"]
        mock_process.open_files.return_value = ["file1", "file2", "file3"]
        mock_process_class.return_value = mock_process

        mock_get_count.return_value = [100, 200, 300]
        mock_get_objects.return_value = ["obj"] * 1500

        # Act
        response = client.get("/debug/stats")

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["memory"]["rss_mb"] == 100.0
        assert data["memory"]["vms_mb"] == 200.0
        assert data["memory"]["percent"] == 5.5

        assert data["cpu"]["percent"] == 15.2
        assert data["cpu"]["num_threads"] == 8

        assert data["gc"]["collections"] == [100, 200, 300]
        assert data["gc"]["objects"] == 1500

        assert data["connections"] == 2
        assert data["open_files"] == 3
        assert "timestamp" in data

    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_debug_stats_forbidden_in_production(self, client):
        """Test debug stats endpoint returns 403 in production."""
        # Act
        response = client.get("/debug/stats")

        # Assert
        assert response.status_code == 403
        data = response.json()
        assert "Debug endpoints disabled in production" in data["error"]

    @patch.dict(os.environ, {}, clear=True)  # Clear ENVIRONMENT var
    @patch("psutil.Process")
    @patch("gc.get_count")
    @patch("gc.get_objects")
    def test_debug_stats_defaults_to_development(
        self, mock_get_objects, mock_get_count, mock_process_class, client
    ):
        """Test debug stats endpoint defaults to development when ENVIRONMENT is not set."""
        # Arrange - minimal setup for default case
        mock_process = MagicMock()
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 0
        mock_memory_info.vms = 0
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.memory_percent.return_value = 0
        mock_process.cpu_percent.return_value = 0
        mock_process.num_threads.return_value = 1
        mock_process.connections.return_value = []
        mock_process.open_files.return_value = []
        mock_process_class.return_value = mock_process
        mock_get_count.return_value = [0, 0, 0]
        mock_get_objects.return_value = []

        # Act
        response = client.get("/debug/stats")

        # Assert
        assert response.status_code == 200


class TestStartupEvent:
    """Test the startup event handler."""

    @patch("ledzephyr.monitoring_api.init_observability")
    def test_startup_event_initializes_observability(self, mock_init_obs):
        """Test startup event initializes observability with correct parameters."""
        # Arrange
        mock_obs = MagicMock()
        mock_init_obs.return_value = mock_obs

        # Act
        import asyncio

        from ledzephyr.monitoring_api import startup_event

        asyncio.run(startup_event())

        # Assert
        mock_init_obs.assert_called_once_with(
            service_name="ledzephyr",
            environment="production",
            enable_tracing=True,
            enable_metrics=True,
        )

    @patch("ledzephyr.monitoring_api.init_observability")
    @patch("ledzephyr.monitoring_api.database_health_check")
    @patch("ledzephyr.monitoring_api.api_health_check")
    @patch("ledzephyr.monitoring_api.cache_health_check")
    def test_startup_event_registers_health_checks(
        self, mock_cache_check, mock_api_check, mock_db_check, mock_init_obs
    ):
        """Test startup event registers all health checks."""
        # Arrange
        mock_obs = MagicMock()
        mock_init_obs.return_value = mock_obs

        # Act
        import asyncio

        from ledzephyr.monitoring_api import startup_event

        asyncio.run(startup_event())

        # Assert
        expected_calls = [
            (("database", mock_db_check),),
            (("api", mock_api_check),),
            (("cache", mock_cache_check),),
        ]

        assert mock_obs.register_health_check.call_count == 3
        actual_calls = mock_obs.register_health_check.call_args_list

        for i, expected_call in enumerate(expected_calls):
            assert actual_calls[i][0] == expected_call[0]


class TestRunMonitoringServer:
    """Test the monitoring server runner function."""

    @patch("ledzephyr.monitoring_api.uvicorn.run")
    def test_run_monitoring_server_with_defaults(self, mock_uvicorn_run):
        """Test monitoring server runs with default parameters."""
        # Arrange
        from ledzephyr.monitoring_api import run_monitoring_server

        # Act
        run_monitoring_server()

        # Assert
        mock_uvicorn_run.assert_called_once_with(
            "ledzephyr.monitoring_api:app",
            host="0.0.0.0",
            port=8080,
            reload=False,
            log_level="info",
        )

    @patch("ledzephyr.monitoring_api.uvicorn.run")
    def test_run_monitoring_server_with_custom_params(self, mock_uvicorn_run):
        """Test monitoring server runs with custom parameters."""
        # Arrange
        from ledzephyr.monitoring_api import run_monitoring_server

        # Act
        run_monitoring_server(host="127.0.0.1", port=9090, reload=True)

        # Assert
        mock_uvicorn_run.assert_called_once_with(
            "ledzephyr.monitoring_api:app",
            host="127.0.0.1",
            port=9090,
            reload=True,
            log_level="info",
        )


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_health_check_with_missing_observability(self, client):
        """Test health check handles missing observability gracefully."""
        # This tests the real behavior when observability is not properly initialized
        with patch("ledzephyr.monitoring_api.get_observability") as mock_get_obs:
            mock_get_obs.side_effect = Exception("Observability not initialized")

            # The endpoint should propagate the exception as it's a critical error
            with pytest.raises(Exception, match="Observability not initialized"):
                client.get("/health")

    def test_metrics_endpoint_with_observability_error(self, client, mock_observability):
        """Test metrics endpoint handles observability errors."""
        # Arrange
        mock_observability.get_metrics_dump.side_effect = Exception("Metrics collection failed")

        # Act & Assert
        # This should either return an error response or handle gracefully
        with pytest.raises(Exception):
            client.get("/metrics")

    def test_readiness_probe_with_empty_health_checks(self, client, mock_observability):
        """Test readiness probe when no health checks are registered."""
        # Arrange
        mock_observability.check_health.return_value = {}

        # Act
        response = client.get("/health/ready")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


class TestTimeoutAndConnectivity:
    """Test timeout and connectivity scenarios."""

    def test_health_check_with_slow_components(self, client, mock_observability):
        """Test health check behavior with slow responding components."""

        # Arrange
        def slow_health_check():
            import time

            time.sleep(0.01)  # Small delay to simulate slow check
            return {
                "database": HealthStatus(
                    name="database",
                    status="healthy",
                    message="Slow but healthy",
                    last_check=datetime.now(),
                ),
            }

        mock_observability.check_health.side_effect = slow_health_check

        # Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_readiness_probe_with_intermittent_failures(self, client, mock_observability):
        """Test readiness probe with intermittent component failures."""
        # Arrange - simulate intermittent database failure
        mock_observability.check_health.return_value = {
            "database": HealthStatus(
                name="database",
                status="unhealthy",
                message="Connection timeout",
                metadata={"last_error": "Timeout after 5s"},
                last_check=datetime.now(),
            ),
            "api": HealthStatus(
                name="api",
                status="healthy",
                message="API responsive",
                last_check=datetime.now(),
            ),
        }

        # Act
        response = client.get("/health/ready")

        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert "database is unhealthy" in data["reason"]


# Integration tests for the complete monitoring stack
class TestMonitoringIntegration:
    """Integration tests for the complete monitoring API."""

    def test_monitoring_endpoints_workflow(self, client, mock_observability):
        """Test complete monitoring workflow with realistic data."""
        # Arrange
        mock_observability.check_health.return_value = {
            "database": HealthStatus(
                name="database",
                status="healthy",
                message="Database operational",
                metadata={"connections": 5, "latency_ms": 12},
                last_check=datetime.now(),
            ),
            "api": HealthStatus(
                name="api",
                status="healthy",
                message="External APIs responsive",
                metadata={"jira": "ok", "zephyr": "ok"},
                last_check=datetime.now(),
            ),
            "cache": HealthStatus(
                name="cache",
                status="healthy",
                message="Cache operational",
                metadata={"hit_ratio": 0.87, "size_mb": 245},
                last_check=datetime.now(),
            ),
        }

        mock_observability.get_metrics_dump.return_value = (
            b"# HELP ledzephyr_api_requests_total Total API requests\n"
            b'ledzephyr_api_requests_total{method="GET",endpoint="/health"} 42\n'
        )

        # Act & Assert - Test complete workflow
        # 1. Check liveness
        live_response = client.get("/health/live")
        assert live_response.status_code == 200
        assert live_response.json()["status"] == "alive"

        # 2. Check readiness
        ready_response = client.get("/health/ready")
        assert ready_response.status_code == 200
        assert ready_response.json()["status"] == "ready"

        # 3. Get detailed health
        health_response = client.get("/health")
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data["status"] == "healthy"
        assert len(health_data["checks"]) == 3

        # 4. Get metrics
        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200
        assert "ledzephyr_api_requests_total" in metrics_response.text

        # 5. Get service info
        info_response = client.get("/info")
        assert info_response.status_code == 200
        info_data = info_response.json()
        assert info_data["service"] == "ledzephyr"


# Note: The main block (if __name__ == "__main__":) is not tested as it's a simple
# invocation for direct script execution and is outside the scope of unit testing.
