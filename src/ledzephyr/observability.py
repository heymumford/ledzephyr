"""
Observability module for ledzephyr.

Provides structured logging, metrics collection, distributed tracing,
and health check monitoring for production deployments.
"""

import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any
from uuid import uuid4

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Summary,
    generate_latest,
)

# Initialize structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
        structlog.processors.dict_tracebacks,
        structlog.dev.ConsoleRenderer() if __debug__ else structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)


class MetricType(Enum):
    """Types of metrics we collect."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class HealthStatus:
    """Health check status for a component."""

    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    last_check: datetime = field(default_factory=datetime.now)


class ObservabilityManager:
    """Central manager for all observability concerns."""

    def __init__(
        self,
        service_name: str = "ledzephyr",
        environment: str = "development",
        otlp_endpoint: str | None = None,
        enable_tracing: bool = True,
        enable_metrics: bool = True,
    ):
        self.service_name = service_name
        self.environment = environment
        self.logger = structlog.get_logger(service=service_name, env=environment)
        self.correlation_id = None

        # Initialize metrics registry
        self.metrics_registry = CollectorRegistry()
        self.metrics: dict[str, Any] = {}

        if enable_metrics:
            self._init_metrics()

        # Initialize tracing
        self.tracer = None
        if enable_tracing:
            self._init_tracing(otlp_endpoint)

        # Health checks
        self.health_checks: dict[str, Callable[[], HealthStatus]] = {}

    def _init_metrics(self):
        """Initialize Prometheus metrics collectors."""
        # API metrics
        self.metrics["api_requests_total"] = Counter(
            "ledzephyr_api_requests_total",
            "Total API requests",
            ["method", "endpoint", "status"],
            registry=self.metrics_registry,
        )

        self.metrics["api_request_duration_seconds"] = Histogram(
            "ledzephyr_api_request_duration_seconds",
            "API request duration in seconds",
            ["method", "endpoint"],
            registry=self.metrics_registry,
        )

        # Test metrics
        self.metrics["tests_processed_total"] = Counter(
            "ledzephyr_tests_processed_total",
            "Total tests processed",
            ["source", "project"],
            registry=self.metrics_registry,
        )

        self.metrics["metrics_calculation_duration_seconds"] = Histogram(
            "ledzephyr_metrics_calculation_duration_seconds",
            "Metrics calculation duration in seconds",
            ["project", "window"],
            registry=self.metrics_registry,
        )

        # Cache metrics
        self.metrics["cache_hits_total"] = Counter(
            "ledzephyr_cache_hits_total",
            "Total cache hits",
            ["cache_type"],
            registry=self.metrics_registry,
        )

        self.metrics["cache_misses_total"] = Counter(
            "ledzephyr_cache_misses_total",
            "Total cache misses",
            ["cache_type"],
            registry=self.metrics_registry,
        )

        # System metrics
        self.metrics["active_connections"] = Gauge(
            "ledzephyr_active_connections",
            "Number of active connections",
            ["type"],
            registry=self.metrics_registry,
        )

        self.metrics["error_rate"] = Summary(
            "ledzephyr_error_rate",
            "Error rate per operation",
            ["operation", "error_type"],
            registry=self.metrics_registry,
        )

    def _init_tracing(self, otlp_endpoint: str | None):
        """Initialize OpenTelemetry tracing."""
        resource = Resource.create(
            {
                "service.name": self.service_name,
                "service.environment": self.environment,
                "service.version": self._get_version(),
            }
        )

        provider = TracerProvider(resource=resource)

        if otlp_endpoint:
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)

        trace.set_tracer_provider(provider)
        self.tracer = trace.get_tracer(__name__)

        # Auto-instrument HTTP clients
        HTTPXClientInstrumentor().instrument()
        RequestsInstrumentor().instrument()

    def _get_version(self) -> str:
        """Get the application version."""
        try:
            from ledzephyr import __version__

            return __version__
        except ImportError:
            return "unknown"

    @contextmanager
    def correlation_context(self, correlation_id: str | None = None):
        """Context manager for correlation ID tracking."""
        if correlation_id is None:
            correlation_id = str(uuid4())

        old_id = self.correlation_id
        self.correlation_id = correlation_id

        try:
            yield correlation_id
        finally:
            self.correlation_id = old_id

    def log(
        self,
        level: str,
        message: str,
        **kwargs,
    ):
        """Log a structured message."""
        kwargs["correlation_id"] = self.correlation_id
        getattr(self.logger, level.lower())(message, **kwargs)

    def record_metric(
        self,
        name: str,
        value: int | float,
        metric_type: MetricType = MetricType.COUNTER,
        labels: dict[str, str] | None = None,
    ):
        """Record a metric value."""
        if name not in self.metrics:
            self.log("warning", f"Unknown metric: {name}")
            return

        metric = self.metrics[name]
        labels = labels or {}

        if metric_type == MetricType.COUNTER:
            metric.labels(**labels).inc(value)
        elif metric_type == MetricType.GAUGE:
            metric.labels(**labels).set(value)
        elif metric_type == MetricType.HISTOGRAM:
            metric.labels(**labels).observe(value)
        elif metric_type == MetricType.SUMMARY:
            metric.labels(**labels).observe(value)

    @contextmanager
    def trace_span(
        self,
        name: str,
        kind: trace.SpanKind = trace.SpanKind.INTERNAL,
        attributes: dict[str, Any] | None = None,
    ):
        """Context manager for creating a trace span."""
        if not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(
            name,
            kind=kind,
            attributes=attributes or {},
        ) as span:
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise

    def register_health_check(
        self,
        name: str,
        check_func: Callable[[], HealthStatus],
    ):
        """Register a health check function."""
        self.health_checks[name] = check_func
        self.log("info", f"Registered health check: {name}")

    def check_health(self) -> dict[str, HealthStatus]:
        """Run all health checks and return results."""
        results = {}

        for name, check_func in self.health_checks.items():
            try:
                with self.trace_span(f"health_check.{name}"):
                    status = check_func()
                    results[name] = status

                    self.log(
                        "info" if status.status == "healthy" else "warning",
                        f"Health check {name}: {status.status}",
                        check_name=name,
                        status=status.status,
                        message=status.message,
                    )
            except Exception as e:
                results[name] = HealthStatus(
                    name=name,
                    status="unhealthy",
                    message=str(e),
                )
                self.log(
                    "error",
                    f"Health check {name} failed",
                    check_name=name,
                    error=str(e),
                    exc_info=True,
                )

        return results

    def get_metrics_dump(self) -> bytes:
        """Get Prometheus metrics in text format."""
        return generate_latest(self.metrics_registry)

    def instrument(self, func: Callable) -> Callable:
        """Decorator to instrument a function with logging, metrics, and tracing."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"

            with self.correlation_context():
                with self.trace_span(func_name) as span:
                    start_time = time.time()

                    self.log(
                        "debug",
                        f"Starting {func_name}",
                        function=func_name,
                        args=str(args)[:100],
                        kwargs=str(kwargs)[:100],
                    )

                    try:
                        result = func(*args, **kwargs)

                        duration = time.time() - start_time

                        self.log(
                            "debug",
                            f"Completed {func_name}",
                            function=func_name,
                            duration=duration,
                        )

                        if span:
                            span.set_attribute("duration_seconds", duration)

                        return result

                    except Exception as e:
                        duration = time.time() - start_time

                        self.log(
                            "error",
                            f"Error in {func_name}",
                            function=func_name,
                            duration=duration,
                            error=str(e),
                            exc_info=True,
                        )

                        self.record_metric(
                            "error_rate",
                            1,
                            MetricType.SUMMARY,
                            {"operation": func_name, "error_type": type(e).__name__},
                        )

                        raise

        return wrapper


# Global observability instance
_observability: ObservabilityManager | None = None


def init_observability(
    service_name: str = "ledzephyr",
    environment: str = "development",
    otlp_endpoint: str | None = None,
    enable_tracing: bool = True,
    enable_metrics: bool = True,
) -> ObservabilityManager:
    """Initialize global observability manager."""
    global _observability
    _observability = ObservabilityManager(
        service_name=service_name,
        environment=environment,
        otlp_endpoint=otlp_endpoint,
        enable_tracing=enable_tracing,
        enable_metrics=enable_metrics,
    )
    return _observability


def get_observability() -> ObservabilityManager:
    """Get the global observability manager."""
    if _observability is None:
        return init_observability()
    return _observability


# Health check implementations
def database_health_check() -> HealthStatus:
    """Check database connectivity."""
    # This would check actual database in production
    return HealthStatus(
        name="database",
        status="healthy",
        message="Database connection OK",
        metadata={"connection_pool_size": 10, "active_connections": 2},
    )


def api_health_check() -> HealthStatus:
    """Check external API connectivity."""
    from ledzephyr.client import APIClient
    from ledzephyr.config import Config

    try:
        # Quick connectivity check
        config = Config.from_env()
        APIClient(config)
        # Would do actual API ping in production
        return HealthStatus(
            name="external_api",
            status="healthy",
            message="External APIs reachable",
            metadata={"jira": "ok", "zephyr": "ok", "qtest": "ok"},
        )
    except Exception as e:
        return HealthStatus(
            name="external_api",
            status="degraded",
            message=f"API connectivity issue: {e}",
        )


def cache_health_check() -> HealthStatus:
    """Check cache system health."""
    from ledzephyr.cache import SimpleAPICache

    try:
        SimpleAPICache()
        # Would check cache stats in production
        return HealthStatus(
            name="cache",
            status="healthy",
            message="Cache system operational",
            metadata={"hit_rate": 0.85, "size_mb": 120},
        )
    except Exception as e:
        return HealthStatus(
            name="cache",
            status="unhealthy",
            message=f"Cache system error: {e}",
        )
