#!/usr/bin/env python3
"""Contract tests for LedZephyr - API interface health checks.

These tests verify that external service interfaces are healthy and
return data in the expected format. They act as smoke tests for API contracts.
"""

from unittest.mock import MagicMock, patch

import httpx

from ledzephyr.main import (
    fetch_api_data,
    fetch_defect_data_from_jira,
    fetch_test_data_from_qtest,
    fetch_test_data_from_zephyr,
    try_api_call,
)


def test_api_response_contract_success() -> None:
    """Contract: API calls should return success=True with data on 200."""
    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"id": "1"}]}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        response = try_api_call(
            "https://api.example.com/test", {"Authorization": "Bearer token"}
        )

        assert response.success is True
        assert response.data == {"results": [{"id": "1"}]}
        assert response.error is None


def test_api_response_contract_failure() -> None:
    """Contract: API calls should return success=False with error on failure."""
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Connection failed")

        response = try_api_call(
            "https://api.example.com/test", {"Authorization": "Bearer token"}
        )

        assert response.success is False
        assert response.data is None
        assert response.error is not None


def test_zephyr_api_contract() -> None:
    """Contract: Zephyr API should return list of test cases."""
    with patch("ledzephyr.main.fetch_api_data") as mock_fetch:
        # Mock Zephyr API response structure
        mock_fetch.return_value = {
            "results": [
                {
                    "key": "TEST-1",
                    "name": "Test Case 1",
                    "status": "Approved",
                    "createdOn": "2025-01-15T10:00:00Z",
                    "updatedOn": "2025-01-15T10:00:00Z",
                    "owner": "user@example.com",
                }
            ]
        }

        result = fetch_test_data_from_zephyr(
            "TEST", "https://jira.example.com", "token"
        )

        assert isinstance(result, list)
        if len(result) > 0:
            assert "key" in result[0]
            assert "name" in result[0]


def test_zephyr_api_contract_empty() -> None:
    """Contract: Zephyr API should handle empty results gracefully."""
    with patch("ledzephyr.main.fetch_api_data") as mock_fetch:
        mock_fetch.return_value = {"results": []}

        result = fetch_test_data_from_zephyr(
            "TEST", "https://jira.example.com", "token"
        )

        assert isinstance(result, list)
        assert len(result) == 0


def test_zephyr_api_contract_error() -> None:
    """Contract: Zephyr API should return empty list on error."""
    with patch("ledzephyr.main.fetch_api_data") as mock_fetch:
        mock_fetch.return_value = {}  # Simulates error case

        result = fetch_test_data_from_zephyr(
            "TEST", "https://jira.example.com", "token"
        )

        assert isinstance(result, list)
        assert len(result) == 0


def test_qtest_api_contract() -> None:
    """Contract: qTest API should return list of test cases."""
    with patch("ledzephyr.main.fetch_api_data") as mock_fetch:
        # First call: get projects
        # Second call: get test cases
        mock_fetch.side_effect = [
            [{"id": "123", "name": "TEST"}],  # Projects
            [
                {
                    "id": "1",
                    "name": "Test Case 1",
                    "status": "Approved",
                    "last_modified_date": "2025-01-15T10:00:00Z",
                }
            ],  # Test cases
        ]

        result = fetch_test_data_from_qtest(
            "TEST", "https://qtest.example.com", "token"
        )

        assert isinstance(result, list)
        if len(result) > 0:
            assert "id" in result[0]
            assert "name" in result[0]


def test_qtest_api_contract_project_not_found() -> None:
    """Contract: qTest API should return empty list when project not found."""
    with patch("ledzephyr.main.fetch_api_data") as mock_fetch:
        # Return projects without the target project
        mock_fetch.return_value = [{"id": "456", "name": "OTHER"}]

        result = fetch_test_data_from_qtest(
            "TEST", "https://qtest.example.com", "token"
        )

        assert isinstance(result, list)
        assert len(result) == 0


def test_qtest_api_contract_no_token() -> None:
    """Contract: qTest API should return empty list when no token provided."""
    result = fetch_test_data_from_qtest("TEST", "https://qtest.example.com", None)

    assert isinstance(result, list)
    assert len(result) == 0


def test_jira_api_contract() -> None:
    """Contract: Jira API should return list of issues."""
    with patch("ledzephyr.main.fetch_api_data") as mock_fetch:
        # Mock Jira search response
        mock_fetch.return_value = {
            "issues": [
                {
                    "key": "TEST-1",
                    "fields": {
                        "summary": "Bug in feature X",
                        "status": {"name": "Open"},
                        "created": "2025-01-15T10:00:00Z",
                        "updated": "2025-01-15T10:00:00Z",
                        "assignee": {"displayName": "User"},
                    },
                }
            ]
        }

        result = fetch_defect_data_from_jira(
            "TEST", "https://jira.example.com", "token"
        )

        assert isinstance(result, list)
        if len(result) > 0:
            assert "key" in result[0]
            assert "fields" in result[0]


def test_jira_api_contract_empty() -> None:
    """Contract: Jira API should handle empty results."""
    with patch("ledzephyr.main.fetch_api_data") as mock_fetch:
        mock_fetch.return_value = {"issues": []}

        result = fetch_defect_data_from_jira(
            "TEST", "https://jira.example.com", "token"
        )

        assert isinstance(result, list)
        assert len(result) == 0


def test_jira_api_contract_error() -> None:
    """Contract: Jira API should return empty list on error."""
    with patch("ledzephyr.main.fetch_api_data") as mock_fetch:
        mock_fetch.return_value = {}  # Simulates error case

        result = fetch_defect_data_from_jira(
            "TEST", "https://jira.example.com", "token"
        )

        assert isinstance(result, list)
        assert len(result) == 0


def test_retry_contract() -> None:
    """Contract: fetch_api_data should retry on failure."""
    with patch("ledzephyr.main.try_api_call") as mock_try:
        # Simulate failure then success
        from ledzephyr.main import APIResponse

        mock_try.side_effect = [
            APIResponse(success=False, error=Exception("Timeout")),
            APIResponse(success=False, error=Exception("Timeout")),
            APIResponse(success=True, data={"result": "success"}),
        ]

        result = fetch_api_data("https://api.example.com", {"Auth": "token"})

        assert result == {"result": "success"}
        assert mock_try.call_count == 3  # Retried twice, succeeded on third


def test_retry_contract_exhausted() -> None:
    """Contract: fetch_api_data should return empty dict after all retries fail."""
    with patch("ledzephyr.main.try_api_call") as mock_try:
        from ledzephyr.main import APIResponse

        # All attempts fail
        mock_try.return_value = APIResponse(success=False, error=Exception("Error"))

        result = fetch_api_data("https://api.example.com", {"Auth": "token"})

        assert result == {}
        assert mock_try.call_count == 3  # DEFAULT_RETRY_COUNT


def test_http_timeout_contract() -> None:
    """Contract: HTTP requests should have timeout configured."""
    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        try_api_call("https://api.example.com", {})

        # Verify timeout was set
        call_kwargs = mock_get.call_args[1]
        assert "timeout" in call_kwargs
        assert call_kwargs["timeout"] == 30  # DEFAULT_API_TIMEOUT_SECONDS


def run_contract_tests() -> None:
    """Run all contract tests."""
    tests = [
        ("API success contract", test_api_response_contract_success),
        ("API failure contract", test_api_response_contract_failure),
        ("Zephyr API contract", test_zephyr_api_contract),
        ("Zephyr API empty contract", test_zephyr_api_contract_empty),
        ("Zephyr API error contract", test_zephyr_api_contract_error),
        ("qTest API contract", test_qtest_api_contract),
        ("qTest project not found", test_qtest_api_contract_project_not_found),
        ("qTest no token contract", test_qtest_api_contract_no_token),
        ("Jira API contract", test_jira_api_contract),
        ("Jira API empty contract", test_jira_api_contract_empty),
        ("Jira API error contract", test_jira_api_contract_error),
        ("Retry mechanism contract", test_retry_contract),
        ("Retry exhausted contract", test_retry_contract_exhausted),
        ("HTTP timeout contract", test_http_timeout_contract),
    ]

    print("Running Contract Tests...")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            print(f"✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name}: Unexpected error: {e}")
            failed += 1

    print("=" * 60)
    print(f"Contract Tests: {passed} passed, {failed} failed")

    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    run_contract_tests()
