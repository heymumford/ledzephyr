"""Tests for the observability module."""

import time
from unittest.mock import Mock, patch

import pytest

from ledzephyr.observability import (
    HealthStatus,
    MetricType,
    ObservabilityManager,
    api_health_check,
    cache_health_check,
    database_health_check,
    get_observability,
    init_observability,
)


class TestObservabilityManager:
    """Test the ObservabilityManager class."""

    def test_initialization(self):
        """Test ObservabilityManager initialization."""
        obs = ObservabilityManager(
            service_name="test-service",
            environment="testing",
            enable_tracing=False,
            enable_metrics=True,
        )

        assert obs.service_name == "test-service"
        assert obs.environment == "testing"
        assert obs.correlation_id is None
        assert obs.tracer is None  # Tracing disabled
        assert len(obs.metrics) > 0  # Metrics enabled

    def test_correlation_context(self):
        """Test correlation ID context manager."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)

        # Test with auto-generated ID
        with obs.correlation_context() as corr_id:
            assert corr_id is not None
            assert obs.correlation_id == corr_id

        assert obs.correlation_id is None  # Reset after context

        # Test with provided ID
        test_id = "test-correlation-123"
        with obs.correlation_context(test_id) as corr_id:
            assert corr_id == test_id
            assert obs.correlation_id == test_id

    def test_logging(self):
        """Test structured logging."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)

        with patch.object(obs.logger, "info") as mock_info:
            obs.log("info", "Test message", key1="value1", key2=42)
            mock_info.assert_called_once()
            args = mock_info.call_args
            assert "Test message" in str(args)
            assert "key1" in str(args)
            assert "value1" in str(args)

    def test_metrics_recording(self):
        """Test metric recording."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=True)

        # Test counter metric
        obs.record_metric(
            "api_requests_total",
            1,
            MetricType.COUNTER,
            {"method": "GET", "endpoint": "test", "status": "200"},
        )

        # Test histogram metric
        obs.record_metric(
            "api_request_duration_seconds",
            0.5,
            MetricType.HISTOGRAM,
            {"method": "GET", "endpoint": "test"},
        )

        # Test gauge metric
        obs.record_metric("active_connections", 5, MetricType.GAUGE, {"type": "api"})

        # Get metrics dump
        metrics_text = obs.get_metrics_dump()
        assert b"ledzephyr_api_requests_total" in metrics_text
        assert b"ledzephyr_api_request_duration_seconds" in metrics_text
        assert b"ledzephyr_active_connections" in metrics_text

    def test_trace_span(self):
        """Test trace span context manager."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)

        # Should not fail when tracing is disabled
        with obs.trace_span("test-span") as span:
            assert span is None

        # Test with mock tracer
        obs.tracer = Mock()
        mock_span = Mock()
        obs.tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_span)
        obs.tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=None)

        with obs.trace_span("test-span", attributes={"key": "value"}) as span:
            assert span == mock_span

    def test_trace_span_exception_handling(self):
        """Test trace span handles exceptions properly."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)

        # Create mock tracer
        obs.tracer = Mock()
        mock_span = Mock()
        obs.tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_span)
        obs.tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=None)

        # Test exception handling
        with pytest.raises(ValueError):
            with obs.trace_span("error-span") as span:
                raise ValueError("Test error")

        mock_span.record_exception.assert_called_once()
        mock_span.set_status.assert_called_once()

    def test_health_check_registration(self):
        """Test health check registration."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)

        def test_health_check():
            return HealthStatus(name="test", status="healthy")

        obs.register_health_check("test", test_health_check)
        assert "test" in obs.health_checks
        assert obs.health_checks["test"] == test_health_check

    def test_health_check_execution(self):
        """Test health check execution."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)

        # Register healthy check
        def healthy_check():
            return HealthStatus(name="healthy", status="healthy", message="All good")

        obs.register_health_check("healthy", healthy_check)

        # Register degraded check
        def degraded_check():
            return HealthStatus(name="degraded", status="degraded", message="Performance issues")

        obs.register_health_check("degraded", degraded_check)

        # Register failing check
        def failing_check():
            raise Exception("Service unavailable")

        obs.register_health_check("failing", failing_check)

        # Run checks
        results = obs.check_health()

        assert len(results) == 3
        assert results["healthy"].status == "healthy"
        assert results["degraded"].status == "degraded"
        assert results["failing"].status == "unhealthy"
        assert "Service unavailable" in results["failing"].message

    def test_instrument_decorator(self):
        """Test function instrumentation decorator."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)

        @obs.instrument
        def test_function(x, y):
            return x + y

        with patch.object(obs, "log") as mock_log:
            result = test_function(2, 3)
            assert result == 5
            # Should log start and completion
            assert mock_log.call_count >= 2

    def test_instrument_decorator_with_exception(self):
        """Test instrumentation decorator handles exceptions."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=True)

        @obs.instrument
        def failing_function():
            raise ValueError("Test error")

        with patch.object(obs, "log") as mock_log:
            with pytest.raises(ValueError):
                failing_function()

            # Should log error
            error_calls = [call for call in mock_log.call_args_list if "error" in str(call)]
            assert len(error_calls) > 0

    def test_global_observability(self):
        """Test global observability instance."""
        # Initialize global instance
        obs1 = init_observability(service_name="global-test", environment="test")
        assert obs1 is not None

        # Get should return same instance
        obs2 = get_observability()
        assert obs2 is obs1

        # Re-init should create new instance
        obs3 = init_observability(service_name="global-test-2", environment="test2")
        assert obs3 is not obs1
        assert obs3.service_name == "global-test-2"


class TestHealthChecks:
    """Test the built-in health check functions."""

    def test_database_health_check(self):
        """Test database health check."""
        status = database_health_check()
        assert status.name == "database"
        assert status.status == "healthy"
        assert status.metadata is not None

    @patch("ledzephyr.observability.Config")
    @patch("ledzephyr.observability.APIClient")
    def test_api_health_check_success(self, mock_client_class, mock_config_class):
        """Test API health check when APIs are reachable."""
        mock_config = Mock()
        mock_config_class.from_env.return_value = mock_config

        status = api_health_check()
        assert status.name == "external_api"
        assert status.status == "healthy"

    @patch("ledzephyr.observability.Config")
    def test_api_health_check_failure(self, mock_config_class):
        """Test API health check when APIs are not reachable."""
        mock_config_class.from_env.side_effect = Exception("Config error")

        status = api_health_check()
        assert status.name == "external_api"
        assert status.status == "degraded"
        assert "Config error" in status.message

    @patch("ledzephyr.observability.SimpleAPICache")
    def test_cache_health_check_success(self, mock_cache_class):
        """Test cache health check when cache is operational."""
        mock_cache_class.return_value = Mock()

        status = cache_health_check()
        assert status.name == "cache"
        assert status.status == "healthy"

    @patch("ledzephyr.observability.SimpleAPICache")
    def test_cache_health_check_failure(self, mock_cache_class):
        """Test cache health check when cache fails."""
        mock_cache_class.side_effect = Exception("Cache error")

        status = cache_health_check()
        assert status.name == "cache"
        assert status.status == "unhealthy"
        assert "Cache error" in status.message


class TestMetricsExport:
    """Test metrics export functionality."""

    def test_prometheus_export_format(self):
        """Test Prometheus metrics export format."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=True)

        # Record some metrics
        obs.record_metric(
            "api_requests_total",
            5,
            MetricType.COUNTER,
            {"method": "GET", "endpoint": "test", "status": "200"},
        )

        # Get metrics
        metrics_data = obs.get_metrics_dump()

        # Check format
        assert isinstance(metrics_data, bytes)
        metrics_text = metrics_data.decode("utf-8")
        assert "# HELP" in metrics_text
        assert "# TYPE" in metrics_text
        assert "ledzephyr_api_requests_total" in metrics_text

    def test_metrics_labels(self):
        """Test that metrics labels are properly recorded."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=True)

        # Record metrics with different labels
        obs.record_metric(
            "tests_processed_total",
            10,
            MetricType.COUNTER,
            {"source": "zephyr", "project": "TEST"},
        )
        obs.record_metric(
            "tests_processed_total",
            20,
            MetricType.COUNTER,
            {"source": "qtest", "project": "TEST"},
        )

        metrics_text = obs.get_metrics_dump().decode("utf-8")
        assert 'source="zephyr"' in metrics_text
        assert 'source="qtest"' in metrics_text
        assert 'project="TEST"' in metrics_text


class TestPerformance:
    """Test performance aspects of observability."""

    def test_minimal_overhead(self):
        """Test that observability adds minimal overhead."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=True)

        @obs.instrument
        def fast_function():
            return sum(range(100))

        # Measure with instrumentation
        start = time.perf_counter()
        for _ in range(100):
            fast_function()
        instrumented_time = time.perf_counter() - start

        # Measure without instrumentation
        def plain_function():
            return sum(range(100))

        start = time.perf_counter()
        for _ in range(100):
            plain_function()
        plain_time = time.perf_counter() - start

        # Overhead should be less than 50% for this simple function
        overhead_ratio = instrumented_time / plain_time
        assert overhead_ratio < 1.5, f"Overhead too high: {overhead_ratio:.2f}x"
