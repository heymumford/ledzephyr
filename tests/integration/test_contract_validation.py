"""
Integration tests for contract testing framework.

These tests validate that our contract testing infrastructure works correctly
and can detect contract violations in API interactions.
"""

import pytest
import tempfile
from pathlib import Path

from tests.integration.doubles.contract_tester import (
    ContractTestSuite,
    ContractViolation,
    ResponseType,
    ContractExpectation,
    JiraContractDefinitions,
    ZephyrContractDefinitions,
    QTestContractDefinitions,
)


class TestContractTestSuite:
    """Test the contract testing framework itself."""

    def test_contract_suite_initialization(self):
        """Test that contract suite initializes with standard expectations."""
        suite = ContractTestSuite()

        # Should have expectations for all three API types
        jira_expectations = len(JiraContractDefinitions.get_standard_expectations())
        zephyr_expectations = len(ZephyrContractDefinitions.get_standard_expectations())
        qtest_expectations = len(QTestContractDefinitions.get_standard_expectations())

        expected_total = jira_expectations + zephyr_expectations + qtest_expectations
        assert len(suite.recorder.expectations) == expected_total

    def test_successful_contract_validation(self):
        """Test contract validation passes for compliant interactions."""
        suite = ContractTestSuite()

        # Mock a compliant Jira authentication
        suite.mock_api_interaction(
            method="GET",
            url="https://example.atlassian.net/rest/api/2/myself",
            headers={"Authorization": "Bearer token123", "Accept": "application/json"},
            response_status=200,
            response_body={
                "accountId": "user123",
                "displayName": "Test User",
                "emailAddress": "test@example.com",
            },
            response_time_ms=150,
        )

        # Validation should pass
        assert suite.validate_all_contracts() is True

    def test_contract_violation_detection(self):
        """Test contract validation detects violations."""
        suite = ContractTestSuite()

        # Mock a non-compliant interaction (missing authentication)
        suite.mock_api_interaction(
            method="GET",
            url="https://example.atlassian.net/rest/api/2/myself",
            headers={"Accept": "application/json"},  # Missing Authorization
            response_status=401,
            response_time_ms=100,
        )

        # Validation should fail
        assert suite.validate_all_contracts() is False

    def test_response_time_violation(self):
        """Test contract validation detects response time violations."""
        suite = ContractTestSuite()

        # Mock an interaction that's too slow
        suite.mock_api_interaction(
            method="GET",
            url="https://example.atlassian.net/rest/api/2/myself",
            headers={"Authorization": "Bearer token123", "Accept": "application/json"},
            response_status=200,
            response_body={
                "accountId": "user123",
                "displayName": "Test User",
                "emailAddress": "test@example.com",
            },
            response_time_ms=5000,  # Exceeds 3000ms limit
        )

        # Validation should fail due to slow response
        assert suite.validate_all_contracts() is False

    def test_contract_report_generation(self):
        """Test contract report generation."""
        suite = ContractTestSuite()

        # Add some interactions
        suite.mock_api_interaction(
            method="GET",
            url="https://example.atlassian.net/rest/api/2/myself",
            headers={"Authorization": "Bearer token123", "Accept": "application/json"},
            response_status=200,
            response_body={
                "accountId": "user123",
                "displayName": "Test User",
                "emailAddress": "test@example.com",
            },
            response_time_ms=150,
        )

        report = suite.generate_contract_report()

        # Verify report structure
        assert "timestamp" in report
        assert "total_interactions" in report
        assert "total_expectations" in report
        assert "violations_count" in report
        assert "pass_rate" in report
        assert "interactions" in report
        assert "expectations" in report

        assert report["total_interactions"] == 1
        assert isinstance(report["pass_rate"], float)

    def test_contract_report_file_save(self):
        """Test saving contract report to file."""
        suite = ContractTestSuite()

        # Add an interaction
        suite.mock_api_interaction(
            method="GET",
            url="https://example.atlassian.net/rest/api/2/myself",
            headers={"Authorization": "Bearer token123", "Accept": "application/json"},
            response_status=200,
            response_body={"accountId": "user123"},
            response_time_ms=150,
        )

        # Save report to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)

        try:
            suite.generate_contract_report(tmp_path)

            # Verify file was created and contains valid JSON
            assert tmp_path.exists()
            assert tmp_path.stat().st_size > 0

            # Verify we can read it back
            import json

            with open(tmp_path, "r") as f:
                saved_report = json.load(f)

            assert "total_interactions" in saved_report
            assert saved_report["total_interactions"] == 1

        finally:
            # Cleanup
            if tmp_path.exists():
                tmp_path.unlink()


class TestJiraContractDefinitions:
    """Test Jira-specific contract definitions."""

    def test_jira_standard_expectations(self):
        """Test Jira standard contract expectations."""
        expectations = JiraContractDefinitions.get_standard_expectations()

        assert len(expectations) > 0

        # Check that all expectations have required fields
        for expectation in expectations:
            assert expectation.method in ["GET", "POST", "PUT", "DELETE"]
            assert expectation.endpoint_pattern
            assert expectation.required_auth is True  # Jira requires auth
            assert expectation.max_response_time_ms > 0

    def test_jira_authentication_expectation(self):
        """Test Jira authentication endpoint expectation."""
        expectations = JiraContractDefinitions.get_standard_expectations()

        auth_expectations = [
            exp for exp in expectations if "/rest/api/2/myself" in exp.endpoint_pattern
        ]

        assert len(auth_expectations) == 1
        auth_exp = auth_expectations[0]

        assert auth_exp.method == "GET"
        assert auth_exp.response_type == ResponseType.SUCCESS
        assert auth_exp.response_status == 200
        assert "accountId" in auth_exp.response_body
        assert "displayName" in auth_exp.response_body


class TestZephyrContractDefinitions:
    """Test Zephyr-specific contract definitions."""

    def test_zephyr_standard_expectations(self):
        """Test Zephyr standard contract expectations."""
        expectations = ZephyrContractDefinitions.get_standard_expectations()

        assert len(expectations) > 0

        # Check that all expectations require Bearer token auth
        for expectation in expectations:
            assert expectation.required_auth is True
            assert any(
                "Authorization" in header and "Bearer" in header_value
                for header, header_value in expectation.expected_headers.items()
            )

    def test_zephyr_health_check_expectation(self):
        """Test Zephyr health check endpoint expectation."""
        expectations = ZephyrContractDefinitions.get_standard_expectations()

        health_expectations = [
            exp for exp in expectations if "/rest/atm/1.0/healthcheck" in exp.endpoint_pattern
        ]

        assert len(health_expectations) == 1
        health_exp = health_expectations[0]

        assert health_exp.method == "GET"
        assert health_exp.response_status == 200


class TestQTestContractDefinitions:
    """Test qTest-specific contract definitions."""

    def test_qtest_standard_expectations(self):
        """Test qTest standard contract expectations."""
        expectations = QTestContractDefinitions.get_standard_expectations()

        assert len(expectations) > 0

        # Check that all expectations require bearer token (lowercase)
        for expectation in expectations:
            assert expectation.required_auth is True
            assert any(
                "Authorization" in header and "bearer" in header_value.lower()
                for header, header_value in expectation.expected_headers.items()
            )

    def test_qtest_user_info_expectation(self):
        """Test qTest user info endpoint expectation."""
        expectations = QTestContractDefinitions.get_standard_expectations()

        user_expectations = [
            exp for exp in expectations if "/api/v3/users/me" in exp.endpoint_pattern
        ]

        assert len(user_expectations) == 1
        user_exp = user_expectations[0]

        assert user_exp.method == "GET"
        assert user_exp.response_status == 200
        assert "id" in user_exp.response_body


class TestContractIntegrationScenarios:
    """Test realistic contract validation scenarios."""

    def test_multi_api_workflow_validation(self):
        """Test contract validation for a multi-API workflow."""
        suite = ContractTestSuite()

        # Simulate a complete workflow: Jira auth + project fetch + Zephyr test retrieval

        # 1. Jira authentication
        suite.mock_api_interaction(
            method="GET",
            url="https://company.atlassian.net/rest/api/2/myself",
            headers={"Authorization": "Bearer jira_token", "Accept": "application/json"},
            response_status=200,
            response_body={
                "accountId": "user123",
                "displayName": "Test User",
                "emailAddress": "user@company.com",
            },
            response_time_ms=250,
        )

        # 2. Jira project fetch
        suite.mock_api_interaction(
            method="GET",
            url="https://company.atlassian.net/rest/api/2/project/PROJ",
            headers={"Authorization": "Bearer jira_token", "Accept": "application/json"},
            response_status=200,
            response_body={
                "key": "PROJ",
                "name": "Test Project",
                "description": "Test project description",
                "lead": {"displayName": "Project Lead"},
                "components": [{"name": "Component1"}],
            },
            response_time_ms=400,
        )

        # 3. Zephyr health check
        suite.mock_api_interaction(
            method="GET",
            url="https://company.atlassian.net/rest/atm/1.0/healthcheck",
            headers={"Authorization": "Bearer zephyr_token"},
            response_status=200,
            response_time_ms=150,
        )

        # 4. Zephyr test case search
        suite.mock_api_interaction(
            method="GET",
            url="https://company.atlassian.net/rest/atm/1.0/testcase/search?projectKey=PROJ&maxResults=1000",
            headers={"Authorization": "Bearer zephyr_token", "Accept": "application/json"},
            response_status=200,
            response_body={"values": [{"id": "1", "key": "PROJ-T1", "name": "Test Case 1"}]},
            response_time_ms=800,
        )

        # All interactions should pass contract validation
        assert suite.validate_all_contracts() is True

        # Generate report
        report = suite.generate_contract_report()
        assert report["total_interactions"] == 4
        assert report["violations_count"] == 0
        assert report["pass_rate"] == 100.0

    def test_error_scenario_validation(self):
        """Test contract validation for error scenarios."""
        suite = ContractTestSuite()

        # Test authentication failure
        suite.mock_api_interaction(
            method="GET",
            url="https://company.atlassian.net/rest/api/2/myself",
            headers={"Authorization": "Bearer invalid_token", "Accept": "application/json"},
            response_status=401,
            response_time_ms=100,
        )

        # This should still pass because 401 is expected for invalid auth
        # The contract expects either success OR proper error handling
        violations = suite.recorder.validate_contracts()

        # We should have some violations because the expectation is for SUCCESS
        # but we got CLIENT_ERROR. This is the correct behavior.
        assert len(violations) > 0

    def test_performance_regression_detection(self):
        """Test contract validation detects performance regressions."""
        suite = ContractTestSuite()

        # Mock a very slow API response
        suite.mock_api_interaction(
            method="GET",
            url="https://company.atlassian.net/rest/api/2/search",
            headers={"Authorization": "Bearer token", "Accept": "application/json"},
            params={"jql": "project = TEST"},
            response_status=200,
            response_body={"issues": [], "total": 0, "maxResults": 50},
            response_time_ms=15000,  # 15 seconds - way too slow
        )

        # Should detect performance violation
        assert suite.validate_all_contracts() is False

        violations = suite.recorder.validate_contracts()
        performance_violations = [v for v in violations if "response time" in v.lower()]
        assert len(performance_violations) > 0
