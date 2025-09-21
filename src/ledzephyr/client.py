"""HTTP API client with retries and backoff."""

import logging
import time
from datetime import datetime
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ledzephyr.cache import get_api_cache
from ledzephyr.config import Config
from ledzephyr.error_handler import (
    RateLimitError,
    get_error_handler,
)
from ledzephyr.models import JiraProject, TestCaseModel
from ledzephyr.rate_limiter import (
    MultiTenantRateLimiter,
    RateLimitConfig,
    RateLimitStrategy,
)

logger = logging.getLogger(__name__)

# Try to import observability, but don't fail if not available
try:
    from ledzephyr.observability import MetricType, get_observability

    HAS_OBSERVABILITY = True
except ImportError:
    HAS_OBSERVABILITY = False


class APIError(Exception):
    """Base exception for API errors."""

    pass


class AuthenticationError(APIError):
    """Authentication failed."""

    pass


class APIClient:
    """HTTP API client with retries and backoff for Jira, Zephyr Scale, and qTest APIs."""

    def __init__(self, config: Config):
        self.config = config
        self._http_client = httpx.Client(
            timeout=config.timeout, headers={"User-Agent": "ledzephyr/0.1.0"}
        )
        self._cache = get_api_cache()
        self._obs = get_observability() if HAS_OBSERVABILITY else None
        self._error_handler = get_error_handler()

        # Initialize rate limiters for different endpoints
        rate_config = RateLimitConfig(
            requests_per_second=10.0,
            burst_size=20,
            strategy=RateLimitStrategy.ADAPTIVE,
        )
        self._rate_limiter = MultiTenantRateLimiter(rate_config)

        # Register circuit breakers for different services
        self._error_handler.register_circuit_breaker(
            "jira_api", failure_threshold=5, recovery_timeout=60
        )
        self._error_handler.register_circuit_breaker(
            "zephyr_api", failure_threshold=5, recovery_timeout=60
        )
        self._error_handler.register_circuit_breaker(
            "qtest_api", failure_threshold=5, recovery_timeout=60
        )

    def __enter__(self) -> "APIClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._http_client.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.3, min=1, max=10),
        retry=retry_if_exception_type(httpx.RequestError),
    )
    def _make_request(
        self,
        method: str,
        url: str,
        auth: tuple | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make HTTP request with retries, rate limiting, and circuit breaking."""
        request_headers = {"Accept": "application/json"}
        if headers:
            request_headers.update(headers)

        logger.debug(f"Making {method} request to {url}")
        start_time = time.time()

        # Extract endpoint and service from URL
        endpoint = url.split("/")[-1] if "/" in url else "unknown"
        service = self._determine_service(url)

        # Check circuit breaker
        breaker = self._error_handler.circuit_breakers.get(f"{service}_api")
        if breaker and breaker.state == "open":
            raise APIError(f"Circuit breaker for {service} is open")

        # Apply rate limiting
        rate_limit_key = f"{service}_{endpoint}"
        if not self._rate_limiter.acquire(rate_limit_key, timeout=2.0):
            raise RateLimitError(f"Rate limit exceeded for {service} {endpoint}", retry_after=2)

        try:
            # Record active connection
            if self._obs:
                self._obs.record_metric("active_connections", 1, MetricType.GAUGE, {"type": "api"})

            response = self._http_client.request(
                method=method, url=url, auth=auth, headers=request_headers, **kwargs
            )

            # Record metrics
            duration = time.time() - start_time
            if self._obs:
                self._obs.record_metric(
                    "api_request_duration_seconds",
                    duration,
                    MetricType.HISTOGRAM,
                    {"method": method, "endpoint": endpoint},
                )
                self._obs.record_metric(
                    "api_requests_total",
                    1,
                    MetricType.COUNTER,
                    {"method": method, "endpoint": endpoint, "status": str(response.status_code)},
                )

            if response.status_code == 401:
                raise AuthenticationError("Authentication failed")
            elif response.status_code == 429:
                # Rate limited by server
                retry_after = response.headers.get("Retry-After", "60")
                self._rate_limiter.record_response(rate_limit_key, False, duration)
                raise RateLimitError(f"Rate limited by {service}", retry_after=int(retry_after))
            elif response.status_code >= 400:
                logger.error(f"HTTP {response.status_code}: {response.text}")
                # Record failure for circuit breaker
                if breaker:
                    breaker._on_failure()
                raise APIError(f"HTTP {response.status_code}: {response.reason_phrase}")

            # Record success for rate limiter and circuit breaker
            self._rate_limiter.record_response(rate_limit_key, True, duration)
            if breaker:
                breaker._on_success()

            return response

        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            # Record failure for circuit breaker
            if breaker:
                breaker._on_failure()
            self._rate_limiter.record_response(rate_limit_key, False, time.time() - start_time)

            if self._obs:
                self._obs.record_metric(
                    "error_rate",
                    1,
                    MetricType.SUMMARY,
                    {"operation": "api_request", "error_type": type(e).__name__},
                )
            raise
        finally:
            # Decrement active connection
            if self._obs:
                self._obs.record_metric("active_connections", -1, MetricType.GAUGE, {"type": "api"})

    def _determine_service(self, url: str) -> str:
        """Determine which service the URL belongs to."""
        if "zephyr" in url.lower() or "scale" in url.lower():
            return "zephyr"
        elif "qtest" in url.lower():
            return "qtest"
        else:
            return "jira"

    def _cached_get(self, url: str, headers: dict[str, str] | None = None) -> dict[str, Any] | None:
        """Make a cached GET request to avoid repeated vendor API calls."""
        request_headers = {"Accept": "application/json"}
        if headers:
            request_headers.update(headers)

        result = self._cache.get_cached_response(url, request_headers)

        # Record cache hit/miss metrics
        if self._obs:
            if result is not None and "_from_cache" in result:
                self._obs.record_metric(
                    "cache_hits_total", 1, MetricType.COUNTER, {"cache_type": "api"}
                )
            else:
                self._obs.record_metric(
                    "cache_misses_total", 1, MetricType.COUNTER, {"cache_type": "api"}
                )

        return result

    def test_jira_connection(self) -> bool:
        """Test Jira API connectivity."""
        try:
            auth = (self.config.jira_username, self.config.jira_api_token)
            response = self._make_request(
                "GET", f"{self.config.jira_url}/rest/api/2/myself", auth=auth
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Jira connection test failed: {e}")
            return False

    def test_zephyr_connection(self) -> bool:
        """Test Zephyr Scale API connectivity."""
        if not self.config.zephyr_token:
            return False

        try:
            headers = {"Authorization": f"Bearer {self.config.zephyr_token}"}
            response = self._make_request(
                "GET",
                f"{self.config.zephyr_url or self.config.jira_url}/rest/atm/1.0/healthcheck",
                headers=headers,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Zephyr connection test failed: {e}")
            return False

    def test_qtest_connection(self) -> bool:
        """Test qTest API connectivity."""
        if not self.config.qtest_token:
            return False

        try:
            headers = {"Authorization": f"bearer {self.config.qtest_token}"}
            response = self._make_request(
                "GET", f"{self.config.qtest_url}/api/v3/users/me", headers=headers
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"qTest connection test failed: {e}")
            return False

    def get_jira_project(self, project_key: str) -> JiraProject:
        """Get Jira project information."""
        auth = (self.config.jira_username, self.config.jira_api_token)
        response = self._make_request(
            "GET", f"{self.config.jira_url}/rest/api/2/project/{project_key}", auth=auth
        )

        data = response.json()
        components = [comp["name"] for comp in data.get("components", [])]

        return JiraProject(
            key=data["key"],
            name=data["name"],
            description=data.get("description"),
            lead=data.get("lead", {}).get("displayName"),
            components=components,
        )

    def get_zephyr_tests(
        self,
        project_key: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[TestCaseModel]:
        """Get test cases from Zephyr Scale."""
        if not self.config.zephyr_token:
            logger.warning("No Zephyr token configured")
            return []

        headers = {"Authorization": f"Bearer {self.config.zephyr_token}"}
        params = {"projectKey": project_key, "maxResults": 1000}

        if start_date:
            params["createdFrom"] = start_date.isoformat()
        if end_date:
            params["createdTo"] = end_date.isoformat()

        try:
            response = self._make_request(
                "GET",
                f"{self.config.zephyr_url or self.config.jira_url}/rest/atm/1.0/testcase/search",
                headers=headers,
                params=params,
            )

            data = response.json()
            tests = []

            for item in data.get("values", []):
                test = TestCaseModel(
                    id=item["id"],
                    key=item["key"],
                    summary=item["name"],
                    project_key=project_key,
                    component=item.get("component"),
                    labels=item.get("labels", []),
                    assignee=item.get("owner", {}).get("displayName"),
                    source_system="zephyr",
                    created=datetime.fromisoformat(item["createdOn"].replace("Z", "+00:00")),
                    updated=datetime.fromisoformat(item["updatedOn"].replace("Z", "+00:00")),
                    status=item["status"],
                    last_execution=None,  # Add missing required field
                    execution_status=None,  # Add missing required field
                )
                tests.append(test)

            return tests

        except Exception as e:
            logger.error(f"Error fetching Zephyr tests: {e}")
            return []

    def get_qtest_tests(
        self,
        project_key: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[TestCaseModel]:
        """Get test cases from qTest."""
        if not self.config.qtest_token:
            logger.warning("No qTest token configured")
            return []

        headers = {"Authorization": f"bearer {self.config.qtest_token}"}

        try:
            # First, get the project ID from qTest
            projects_response = self._make_request(
                "GET", f"{self.config.qtest_url}/api/v3/projects", headers=headers
            )

            qtest_project_id = None
            for project in projects_response.json():
                if project.get("name") == project_key or str(project.get("id")) == project_key:
                    qtest_project_id = project["id"]
                    break

            if not qtest_project_id:
                logger.warning(f"Project {project_key} not found in qTest")
                return []

            # Get test cases for the project
            params = {"pageSize": 1000, "page": 1}

            response = self._make_request(
                "GET",
                f"{self.config.qtest_url}/api/v3/projects/{qtest_project_id}/test-cases",
                headers=headers,
                params=params,
            )

            data = response.json()
            tests = []

            for item in data.get("items", []):
                test = TestCaseModel(
                    id=str(item["id"]),
                    key=f"TC-{item['id']}",
                    summary=item["name"],
                    project_key=project_key,
                    component=None,  # Add missing required field
                    labels=item.get("tags", []),
                    assignee=None,  # Add missing required field
                    source_system="qtest",
                    created=datetime.fromisoformat(item["created_date"].replace("Z", "+00:00")),
                    updated=datetime.fromisoformat(
                        item["last_modified_date"].replace("Z", "+00:00")
                    ),
                    status=item.get("status", "Draft"),
                    last_execution=None,  # Add missing required field
                    execution_status=None,  # Add missing required field
                )
                tests.append(test)

            return tests

        except Exception as e:
            logger.error(f"Error fetching qTest tests: {e}")
            return []

    def get_test_executions(
        self, project_key: str, test_ids: list[str], source_system: str = "zephyr"
    ) -> dict[str, Any]:
        """Get test execution data."""
        if source_system == "zephyr" and self.config.zephyr_token:
            return self._get_zephyr_executions(project_key, test_ids)
        elif source_system == "qtest" and self.config.qtest_token:
            return self._get_qtest_executions(project_key, test_ids)
        else:
            return {}

    def _get_zephyr_executions(self, project_key: str, test_ids: list[str]) -> dict[str, Any]:
        """Get Zephyr Scale execution data."""
        headers = {"Authorization": f"Bearer {self.config.zephyr_token}"}
        executions = {}

        for test_id in test_ids:
            try:
                response = self._make_request(
                    "GET",
                    f"{self.config.zephyr_url or self.config.jira_url}/rest/atm/1.0/testrun/search",
                    headers=headers,
                    params={"testCaseKey": test_id, "maxResults": 1},
                )

                data = response.json()
                if data.get("values"):
                    execution = data["values"][0]
                    executions[test_id] = {
                        "last_execution": execution.get("executedOn"),
                        "status": execution.get("status"),
                        "linked_defects": execution.get("issues", []),
                    }
            except Exception as e:
                logger.debug(f"No execution data for {test_id}: {e}")

        return executions

    def _get_qtest_executions(self, project_key: str, test_ids: list[str]) -> dict[str, Any]:
        """Get qTest execution data."""
        # Simplified implementation - would need project-specific logic
        return {}
