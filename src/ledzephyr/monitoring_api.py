"""
Monitoring API endpoints for ledzephyr.

Provides health check, metrics, and diagnostic endpoints
for monitoring and observability.
"""

from datetime import datetime
from typing import Any

import uvicorn
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from ledzephyr import __version__
from ledzephyr.observability import (
    CONTENT_TYPE_LATEST,
    api_health_check,
    cache_health_check,
    database_health_check,
    get_observability,
    init_observability,
)

app = FastAPI(
    title="Ledzephyr Monitoring API",
    version=__version__,
    description="Health checks and metrics for ledzephyr",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize observability on startup."""
    obs = init_observability(
        service_name="ledzephyr",
        environment="production",
        enable_tracing=True,
        enable_metrics=True,
    )

    # Register health checks
    obs.register_health_check("database", database_health_check)
    obs.register_health_check("api", api_health_check)
    obs.register_health_check("cache", cache_health_check)


@app.get("/health", response_model=dict[str, Any])
async def health_check():
    """
    Comprehensive health check endpoint.

    Returns overall health status and individual component statuses.
    """
    obs = get_observability()
    checks = obs.check_health()

    # Determine overall health
    overall = "healthy"
    for check in checks.values():
        if check.status == "unhealthy":
            overall = "unhealthy"
            break
        elif check.status == "degraded" and overall == "healthy":
            overall = "degraded"

    response = {
        "status": overall,
        "timestamp": datetime.now().isoformat(),
        "version": __version__,
        "checks": {
            name: {
                "status": check.status,
                "message": check.message,
                "metadata": check.metadata,
                "last_check": check.last_check.isoformat(),
            }
            for name, check in checks.items()
        },
    }

    # Set appropriate status code
    status_code = status.HTTP_200_OK
    if overall == "degraded":
        status_code = status.HTTP_207_MULTI_STATUS
    elif overall == "unhealthy":
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=response, status_code=status_code)


@app.get("/health/live", response_model=dict[str, str])
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.

    Simple check to verify the service is running.
    """
    return {"status": "alive", "timestamp": datetime.now().isoformat()}


@app.get("/health/ready", response_model=dict[str, str])
async def readiness_probe():
    """
    Kubernetes readiness probe endpoint.

    Checks if the service is ready to handle requests.
    """
    obs = get_observability()
    checks = obs.check_health()

    # Service is ready if critical components are healthy
    critical_checks = ["database", "api"]
    for check_name in critical_checks:
        if check_name in checks and checks[check_name].status == "unhealthy":
            return JSONResponse(
                content={
                    "status": "not_ready",
                    "reason": f"{check_name} is unhealthy",
                    "timestamp": datetime.now().isoformat(),
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    return {"status": "ready", "timestamp": datetime.now().isoformat()}


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format.
    """
    obs = get_observability()
    metrics_data = obs.get_metrics_dump()

    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/info", response_model=dict[str, Any])
async def service_info():
    """
    Service information endpoint.

    Returns version and runtime information.
    """
    import platform
    import sys
    from pathlib import Path

    return {
        "service": "ledzephyr",
        "version": __version__,
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "hostname": platform.node(),
        "working_directory": str(Path.cwd()),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/debug/config", response_model=dict[str, Any])
async def debug_config():
    """
    Debug endpoint to show current configuration.

    Only available in non-production environments.
    """
    import os

    from ledzephyr.config import Config

    # Only show in development/staging
    if os.getenv("ENVIRONMENT", "development") == "production":
        return JSONResponse(
            content={"error": "Debug endpoints disabled in production"},
            status_code=status.HTTP_403_FORBIDDEN,
        )

    try:
        config = Config.from_env()
        # Redact sensitive values
        config_dict = config.model_dump()
        for key in ["jira_api_token", "zephyr_token", "qtest_token"]:
            if key in config_dict and config_dict[key]:
                config_dict[key] = "***REDACTED***"

        return config_dict
    except Exception as e:
        return {"error": f"Could not load config: {e}"}


@app.get("/debug/stats", response_model=dict[str, Any])
async def debug_stats():
    """
    Debug endpoint with runtime statistics.

    Only available in non-production environments.
    """
    import gc
    import os

    import psutil

    # Only show in development/staging
    if os.getenv("ENVIRONMENT", "development") == "production":
        return JSONResponse(
            content={"error": "Debug endpoints disabled in production"},
            status_code=status.HTTP_403_FORBIDDEN,
        )

    process = psutil.Process()

    return {
        "memory": {
            "rss_mb": process.memory_info().rss / 1024 / 1024,
            "vms_mb": process.memory_info().vms / 1024 / 1024,
            "percent": process.memory_percent(),
        },
        "cpu": {
            "percent": process.cpu_percent(),
            "num_threads": process.num_threads(),
        },
        "gc": {
            "collections": gc.get_count(),
            "objects": len(gc.get_objects()),
        },
        "connections": len(process.connections()),
        "open_files": len(process.open_files()),
        "timestamp": datetime.now().isoformat(),
    }


def run_monitoring_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    reload: bool = False,
):
    """Run the monitoring API server."""
    uvicorn.run(
        "ledzephyr.monitoring_api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    run_monitoring_server()
