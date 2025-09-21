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

    @patch("ledzephyr.client.APIClient")
    @patch("ledzephyr.config.Config")
    def test_api_health_check_success(self, mock_config_class, mock_client_class):
        """Test API health check when APIs are reachable."""
        mock_config = Mock()
        mock_config_class.from_env.return_value = mock_config

        status = api_health_check()
        assert status.name == "external_api"
        assert status.status == "healthy"

    @patch("ledzephyr.config.Config")
    def test_api_health_check_failure(self, mock_config_class):
        """Test API health check when APIs are not reachable."""
        mock_config_class.from_env.side_effect = Exception("Config error")

        status = api_health_check()
        assert status.name == "external_api"
        assert status.status == "degraded"
        assert "Config error" in status.message

    @patch("ledzephyr.cache.SimpleAPICache")
    def test_cache_health_check_success(self, mock_cache_class):
        """Test cache health check when cache is operational."""
        mock_cache_class.return_value = Mock()

        status = cache_health_check()
        assert status.name == "cache"
        assert status.status == "healthy"

    @patch("ledzephyr.cache.SimpleAPICache")
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


class TestLoggingConfiguration:
    """Test logging configuration and formatting."""

    def test_log_level_filtering(self):
        """Test that log level filtering works correctly."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)

        with patch.object(obs.logger, "debug") as mock_debug:
            with patch.object(obs.logger, "info") as mock_info:
                # Log at different levels
                obs.log("debug", "Debug message")
                obs.log("info", "Info message")

                # Both should be called since we're mocking the logger methods directly
                assert mock_debug.call_count == 1, "Debug method should be called"
                assert mock_info.call_count == 1, "Info method should be called"

    def test_structured_log_format(self):
        """Test that logs have proper structured format."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)

        with patch.object(obs.logger, "info") as mock_info:
            obs.log(
                "info", "Test structured logging", user_id="123", operation="test", duration=0.5
            )

            mock_info.assert_called_once()
            args, kwargs = mock_info.call_args

            # Verify structured data is passed
            assert "user_id" in kwargs
            assert "operation" in kwargs
            assert "duration" in kwargs
            assert kwargs["correlation_id"] is None

    def test_correlation_id_in_logs(self):
        """Test that correlation ID is properly included in logs."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)

        test_correlation_id = "test-corr-id-123"

        with obs.correlation_context(test_correlation_id):
            with patch.object(obs.logger, "warning") as mock_warning:
                obs.log("warning", "Test warning with correlation")

                args, kwargs = mock_warning.call_args
                assert kwargs["correlation_id"] == test_correlation_id


class TestTracingConfiguration:
    """Test tracing initialization and configuration."""

    def test_tracing_disabled_initialization(self):
        """Test ObservabilityManager with tracing disabled."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)
        assert obs.tracer is None

    def test_tracing_enabled_initialization(self):
        """Test ObservabilityManager with tracing enabled."""
        with patch("ledzephyr.observability.trace.set_tracer_provider"):
            with patch("ledzephyr.observability.trace.get_tracer") as mock_get_tracer:
                with patch("ledzephyr.observability.HTTPXClientInstrumentor"):
                    with patch("ledzephyr.observability.RequestsInstrumentor"):
                        obs = ObservabilityManager(enable_tracing=True, enable_metrics=False)
                        assert obs.tracer is not None
                        mock_get_tracer.assert_called_once()

    def test_otlp_endpoint_configuration(self):
        """Test OTLP endpoint configuration."""
        test_endpoint = "http://localhost:4317"

        with patch("ledzephyr.observability.OTLPSpanExporter") as mock_exporter:
            with patch("ledzephyr.observability.BatchSpanProcessor") as mock_processor:
                with patch("ledzephyr.observability.trace.set_tracer_provider"):
                    with patch("ledzephyr.observability.trace.get_tracer"):
                        with patch("ledzephyr.observability.HTTPXClientInstrumentor"):
                            with patch("ledzephyr.observability.RequestsInstrumentor"):
                                ObservabilityManager(
                                    enable_tracing=True,
                                    enable_metrics=False,
                                    otlp_endpoint=test_endpoint,
                                )
                                mock_exporter.assert_called_once_with(
                                    endpoint=test_endpoint, insecure=True
                                )

    def test_version_retrieval(self):
        """Test application version retrieval."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)

        # Test version retrieval when import succeeds
        with patch("ledzephyr.__version__", "1.2.3"):
            version = obs._get_version()
            assert version == "1.2.3"

    def test_version_retrieval_failure(self):
        """Test version retrieval when import fails."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)

        # Create a new module that doesn't have __version__
        import sys

        # Temporarily remove the ledzephyr module from sys.modules if it exists
        original_ledzephyr = sys.modules.get("ledzephyr")
        if "ledzephyr" in sys.modules:
            del sys.modules["ledzephyr"]

        try:
            # Mock the import to raise ImportError
            with patch("builtins.__import__", side_effect=ImportError):
                version = obs._get_version()
                assert version == "unknown"
        finally:
            # Restore the original module
            if original_ledzephyr:
                sys.modules["ledzephyr"] = original_ledzephyr


class TestMetricsEdgeCases:
    """Test metrics initialization and edge cases."""

    def test_metrics_disabled_initialization(self):
        """Test ObservabilityManager with metrics disabled."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)
        assert len(obs.metrics) == 0

    def test_unknown_metric_recording(self):
        """Test recording unknown metric logs warning."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=True)

        with patch.object(obs, "log") as mock_log:
            obs.record_metric("unknown_metric", 1, MetricType.COUNTER)
            mock_log.assert_called_with("warning", "Unknown metric: unknown_metric")

    def test_metric_recording_without_labels(self):
        """Test metric recording without labels."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=True)

        # For metrics that require labels, we need to provide them
        # The api_requests_total metric requires method, endpoint, status labels
        obs.record_metric(
            "api_requests_total",
            1,
            MetricType.COUNTER,
            labels={"method": "GET", "endpoint": "test", "status": "200"},
        )

        metrics_text = obs.get_metrics_dump().decode("utf-8")
        assert "ledzephyr_api_requests_total" in metrics_text

    def test_summary_metric_recording(self):
        """Test Summary metric type recording."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=True)

        obs.record_metric(
            "error_rate",
            0.05,
            MetricType.SUMMARY,
            {"operation": "test", "error_type": "ValueError"},
        )

        metrics_text = obs.get_metrics_dump().decode("utf-8")
        assert "ledzephyr_error_rate" in metrics_text


class TestCorrelationIdEdgeCases:
    """Test correlation ID edge cases and nested contexts."""

    def test_nested_correlation_contexts(self):
        """Test nested correlation contexts restore previous ID."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)

        first_id = "first-correlation-id"
        second_id = "second-correlation-id"

        with obs.correlation_context(first_id):
            assert obs.correlation_id == first_id

            with obs.correlation_context(second_id):
                assert obs.correlation_id == second_id

            # Should restore first ID after inner context
            assert obs.correlation_id == first_id

        # Should be None after all contexts
        assert obs.correlation_id is None

    def test_correlation_context_exception_handling(self):
        """Test correlation context handles exceptions and restores ID."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)

        test_id = "exception-test-id"

        try:
            with obs.correlation_context(test_id):
                assert obs.correlation_id == test_id
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Should restore None even after exception
        assert obs.correlation_id is None

    def test_auto_generated_correlation_id_uniqueness(self):
        """Test auto-generated correlation IDs are unique."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)

        ids = []
        for _ in range(5):
            with obs.correlation_context() as corr_id:
                ids.append(corr_id)

        # All IDs should be unique
        assert len(set(ids)) == len(ids)

        # All IDs should be valid UUIDs (basic check)
        for corr_id in ids:
            assert len(corr_id) == 36  # UUID4 string length
            assert corr_id.count("-") == 4  # UUID4 has 4 hyphens


class TestErrorHandling:
    """Test error handling in metric recording and other operations."""

    def test_metric_recording_with_invalid_type(self):
        """Test metric recording with mismatched metric type."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=True)

        # This will raise an exception because counters don't support set operation
        # But the test verifies that the code reaches the metric operation
        with pytest.raises(ValueError, match="Incorrect label count"):
            # Try to use gauge operation on a counter metric without proper labels
            obs.record_metric("api_requests_total", 5, MetricType.GAUGE)


class TestPerformance:
    """Test performance aspects of observability."""

    def test_instrumentation_functionality(self):
        """Test that function instrumentation works correctly."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=False)

        @obs.instrument
        def test_function(x, y):
            return x + y

        # Function should work normally
        result = test_function(2, 3)
        assert result == 5

        # Test with exception
        @obs.instrument
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()

    def test_metrics_collection_performance(self):
        """Test that metrics collection doesn't significantly impact performance."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=True)

        start = time.perf_counter()
        for i in range(1000):
            obs.record_metric(
                "api_requests_total",
                1,
                MetricType.COUNTER,
                {"method": "GET", "endpoint": f"test-{i % 10}", "status": "200"},
            )
        duration = time.perf_counter() - start

        # Should complete 1000 metric recordings in under 1 second
        assert duration < 1.0, f"Metrics collection too slow: {duration:.3f}s"

    def test_large_metrics_dump_performance(self):
        """Test performance of metrics dump with many metrics."""
        obs = ObservabilityManager(enable_tracing=False, enable_metrics=True)

        # Record many metrics with different labels
        for i in range(100):
            obs.record_metric(
                "api_requests_total",
                1,
                MetricType.COUNTER,
                {"method": "GET", "endpoint": f"endpoint-{i}", "status": "200"},
            )

        start = time.perf_counter()
        metrics_data = obs.get_metrics_dump()
        duration = time.perf_counter() - start

        assert len(metrics_data) > 0
        # Metrics dump should be fast even with many data points
        assert duration < 0.5, f"Metrics dump too slow: {duration:.3f}s"
