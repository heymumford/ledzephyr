"""
Spy transport layer for capturing request metadata.
"""

import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class RequestMetadata:
    """Captured request metadata."""

    timestamp: str
    method: str
    url: str
    headers: dict[str, str]
    params: dict[str, Any]
    body: Any | None
    response_status: int
    response_time_ms: float
    call_number: int
    pagination_info: dict[str, Any] | None = None


class SpyTransport:
    """Spy transport layer that captures all request metadata."""

    def __init__(self, backend: Any):
        """
        Initialize spy transport.

        Args:
            backend: The actual API implementation (stub, fake, or real)
        """
        self.backend = backend
        self.request_log: list[RequestMetadata] = []
        self.call_count = 0

        # Assertion helpers
        self.pagination_calls = []
        self.auth_headers = []
        self.rate_limit_headers = []

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_data: Any | None = None,
    ) -> dict[str, Any]:
        """Capture request metadata and delegate to backend."""
        start_time = time.time()
        self.call_count += 1

        # Capture auth headers
        if headers:
            if "Authorization" in headers:
                self.auth_headers.append(headers["Authorization"])
            if "X-RateLimit-Remaining" in headers:
                self.rate_limit_headers.append(headers["X-RateLimit-Remaining"])

        # Detect pagination
        pagination_info = None
        if params:
            if "startAt" in params or "page" in params or "offset" in params:
                pagination_info = {
                    "startAt": params.get("startAt"),
                    "page": params.get("page"),
                    "offset": params.get("offset"),
                    "limit": params.get("maxResults")
                    or params.get("pageSize")
                    or params.get("limit"),
                }
                self.pagination_calls.append(pagination_info)

        # Delegate to backend
        try:
            # Map URL to backend method
            response = self._route_to_backend(method, url, params, json_data)
            response_status = 200
        except Exception as e:
            response = {"error": str(e)}
            response_status = self._extract_status_from_error(str(e))

        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000

        # Log request metadata
        metadata = RequestMetadata(
            timestamp=datetime.now(UTC).isoformat(),
            method=method,
            url=url,
            headers=headers or {},
            params=params or {},
            body=json_data,
            response_status=response_status,
            response_time_ms=response_time_ms,
            call_number=self.call_count,
            pagination_info=pagination_info,
        )
        self.request_log.append(metadata)

        if response_status != 200:
            raise Exception(response["error"])

        return response

    def _route_to_backend(
        self, method: str, url: str, params: dict | None, body: Any | None
    ) -> dict[str, Any]:
        """Route request to appropriate backend method."""
        # Parse URL path
        path_parts = url.split("/")

        # Jira-style routing
        if "/rest/api/3/" in url:
            if "project" in url:
                project_key = path_parts[-1]
                return self.backend.get_project(project_key)
            elif "search" in url:
                return self.backend.search_issues(
                    jql=params.get("jql", ""),
                    start_at=params.get("startAt", 0),
                    max_results=params.get("maxResults", 50),
                )
            elif "issue" in url and method == "GET":
                issue_key = path_parts[-1]
                return self.backend.get_issue(issue_key)
            elif "issue" in url and method == "POST":
                return self.backend.create_issue(body)
            elif "issue" in url and method == "PUT":
                issue_key = path_parts[-1]
                return self.backend.update_issue(issue_key, body)
            elif "myself" in url:
                return self.backend.get_myself()

        # Zephyr-style routing
        elif "/testcases" in url:
            if method == "GET":
                return self.backend.get_testcases(
                    project_id=params.get("projectId", 10001),
                    start_at=params.get("startAt", 0),
                    max_results=params.get("maxResults", 50),
                )
            elif method == "POST":
                return self.backend.create_testcase(
                    project_id=params.get("projectId", 10001), testcase_data=body
                )
        elif "/testcycles" in url:
            return self.backend.get_testcycles(
                project_id=params.get("projectId", 10001),
                start_at=params.get("startAt", 0),
                max_results=params.get("maxResults", 50),
            )
        elif "/testexecutions" in url:
            return self.backend.get_testexecutions(
                project_id=params.get("projectId", 10001),
                start_at=params.get("startAt", 0),
                max_results=params.get("maxResults", 50),
            )

        # qTest-style routing
        elif "/api/v3/projects" in url:
            if len(path_parts) == 4:  # /api/v3/projects
                return {"items": self.backend.get_projects()}
            elif "test-cases" in url:
                project_id = int(path_parts[-3])
                return self.backend.get_test_cases(
                    project_id=project_id,
                    page=params.get("page", 1),
                    size=params.get("pageSize", 100),
                )
            elif "test-runs" in url:
                project_id = int(path_parts[-3])
                return self.backend.get_test_runs(
                    project_id=project_id,
                    page=params.get("page", 1),
                    size=params.get("pageSize", 100),
                )
            elif "test-cycles" in url:
                project_id = int(path_parts[-3])
                return self.backend.get_test_cycles(
                    project_id=project_id,
                    page=params.get("page", 1),
                    size=params.get("pageSize", 100),
                )

        raise Exception(f"404 Not Found: Unknown endpoint {url}")

    def _extract_status_from_error(self, error_msg: str) -> int:
        """Extract HTTP status code from error message."""
        if "401" in error_msg:
            return 401
        elif "404" in error_msg:
            return 404
        elif "429" in error_msg:
            return 429
        elif "500" in error_msg:
            return 500
        else:
            return 500

    # Assertion helpers
    def assert_pagination_used(self) -> bool:
        """Assert that pagination was used in requests."""
        return len(self.pagination_calls) > 0

    def assert_pagination_sequence(self) -> bool:
        """Assert that pagination followed correct sequence."""
        if not self.pagination_calls:
            return False

        # Check if startAt/page values are sequential
        for i in range(1, len(self.pagination_calls)):
            prev = self.pagination_calls[i - 1]
            curr = self.pagination_calls[i]

            if prev.get("startAt") is not None and curr.get("startAt") is not None:
                # For offset-based pagination
                expected_offset = prev["startAt"] + (prev.get("limit") or 50)
                if curr["startAt"] != expected_offset:
                    return False
            elif prev.get("page") is not None and curr.get("page") is not None:
                # For page-based pagination
                if curr["page"] != prev["page"] + 1:
                    return False

        return True

    def assert_auth_headers_present(self) -> bool:
        """Assert that all requests included auth headers."""
        return len(self.auth_headers) == self.call_count

    def assert_rate_limit_respected(self, max_rps: int = 10) -> bool:
        """Assert that request rate stayed below limit."""
        if len(self.request_log) < 2:
            return True

        # Calculate requests per second over windows
        for i in range(1, len(self.request_log)):
            time_diff = (
                datetime.fromisoformat(self.request_log[i].timestamp)
                - datetime.fromisoformat(self.request_log[i - 1].timestamp)
            ).total_seconds()

            if time_diff > 0:
                rps = 1 / time_diff
                if rps > max_rps:
                    return False

        return True

    def get_request_summary(self) -> dict[str, Any]:
        """Get summary of captured requests."""
        return {
            "total_requests": self.call_count,
            "unique_endpoints": len(set(r.url for r in self.request_log)),
            "methods_used": list(set(r.method for r in self.request_log)),
            "avg_response_time_ms": (
                sum(r.response_time_ms for r in self.request_log) / len(self.request_log)
                if self.request_log
                else 0
            ),
            "pagination_calls": len(self.pagination_calls),
            "auth_headers_sent": len(self.auth_headers),
            "error_responses": len([r for r in self.request_log if r.response_status >= 400]),
        }

    def get_request_log_as_dict(self) -> list[dict[str, Any]]:
        """Get request log as list of dicts for serialization."""
        return [asdict(r) for r in self.request_log]

    def clear(self):
        """Clear all captured data."""
        self.request_log.clear()
        self.pagination_calls.clear()
        self.auth_headers.clear()
        self.rate_limit_headers.clear()
        self.call_count = 0
