"""
Contract testing framework for API interactions.

This module provides contract testing capabilities to ensure that our API clients
properly follow external service contracts and handle all expected scenarios.
"""

import json
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


class ContractViolation(Exception):
    """Raised when a contract test fails."""

    pass


class ResponseType(Enum):
    """Types of responses that can be tested."""

    SUCCESS = "success"
    CLIENT_ERROR = "client_error"  # 4xx
    SERVER_ERROR = "server_error"  # 5xx
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"


@dataclass
class ContractExpectation:
    """Defines expected behavior for an API contract."""

    method: str
    endpoint_pattern: str
    expected_headers: Dict[str, str]
    expected_params: Optional[Dict[str, Any]] = None
    expected_body: Optional[Dict[str, Any]] = None
    response_type: ResponseType = ResponseType.SUCCESS
    response_status: int = 200
    response_body: Optional[Dict[str, Any]] = None
    response_headers: Optional[Dict[str, str]] = None
    max_response_time_ms: int = 5000
    required_auth: bool = True


@dataclass
class ContractInteraction:
    """Records an actual API interaction for contract validation."""

    timestamp: datetime
    method: str
    url: str
    headers: Dict[str, str]
    params: Optional[Dict[str, Any]]
    body: Optional[Dict[str, Any]]
    response_status: int
    response_headers: Dict[str, str]
    response_body: Optional[Dict[str, Any]]
    response_time_ms: int
    auth_provided: bool


class ContractTestRecorder:
    """Records API interactions for contract validation."""

    def __init__(self):
        self.interactions: List[ContractInteraction] = []
        self.expectations: List[ContractExpectation] = []

    def add_expectation(self, expectation: ContractExpectation) -> None:
        """Add a contract expectation."""
        self.expectations.append(expectation)

    def record_interaction(self, interaction: ContractInteraction) -> None:
        """Record an API interaction."""
        self.interactions.append(interaction)

    def validate_contracts(self) -> List[str]:
        """Validate all recorded interactions against expectations."""
        violations = []

        for interaction in self.interactions:
            for expectation in self.expectations:
                if self._matches_pattern(interaction, expectation):
                    contract_violations = self._validate_interaction(interaction, expectation)
                    violations.extend(contract_violations)

        return violations

    def _matches_pattern(
        self, interaction: ContractInteraction, expectation: ContractExpectation
    ) -> bool:
        """Check if an interaction matches an expectation pattern."""
        # Simple pattern matching - could be enhanced with regex
        return (
            interaction.method.upper() == expectation.method.upper()
            and expectation.endpoint_pattern in interaction.url
        )

    def _validate_interaction(
        self, interaction: ContractInteraction, expectation: ContractExpectation
    ) -> List[str]:
        """Validate a single interaction against an expectation."""
        violations = []

        # Validate authentication
        if expectation.required_auth and not interaction.auth_provided:
            violations.append(
                f"Authentication required but not provided for {interaction.method} {interaction.url}"
            )

        # Validate response status
        if expectation.response_type == ResponseType.SUCCESS:
            if interaction.response_status >= 400:
                violations.append(f"Expected success but got status {interaction.response_status}")
        elif expectation.response_type == ResponseType.CLIENT_ERROR:
            if not (400 <= interaction.response_status < 500):
                violations.append(
                    f"Expected client error but got status {interaction.response_status}"
                )
        elif expectation.response_type == ResponseType.SERVER_ERROR:
            if not (500 <= interaction.response_status < 600):
                violations.append(
                    f"Expected server error but got status {interaction.response_status}"
                )

        # Validate response time
        if interaction.response_time_ms > expectation.max_response_time_ms:
            violations.append(
                f"Response time {interaction.response_time_ms}ms exceeds limit {expectation.max_response_time_ms}ms"
            )

        # Validate required headers
        for header, expected_value in expectation.expected_headers.items():
            if header not in interaction.headers:
                violations.append(f"Required header '{header}' missing")
            elif interaction.headers[header] != expected_value:
                violations.append(
                    f"Header '{header}' value mismatch: expected '{expected_value}', got '{interaction.headers[header]}'"
                )

        # Validate response body structure (if specified)
        if expectation.response_body and interaction.response_body:
            body_violations = self._validate_response_structure(
                interaction.response_body,
                expectation.response_body,
                f"{interaction.method} {interaction.url}",
            )
            violations.extend(body_violations)

        return violations

    def _validate_response_structure(
        self, actual: Dict[str, Any], expected: Dict[str, Any], context: str
    ) -> List[str]:
        """Validate response body structure."""
        violations = []

        for key, expected_value in expected.items():
            if key not in actual:
                violations.append(f"Missing field '{key}' in response for {context}")
            elif isinstance(expected_value, dict) and isinstance(actual[key], dict):
                # Recursive validation for nested objects
                nested_violations = self._validate_response_structure(
                    actual[key], expected_value, f"{context}.{key}"
                )
                violations.extend(nested_violations)
            elif expected_value is not None and type(actual[key]) != type(expected_value):
                violations.append(
                    f"Type mismatch for field '{key}' in {context}: expected {type(expected_value)}, got {type(actual[key])}"
                )

        return violations

    def generate_contract_report(self) -> Dict[str, Any]:
        """Generate a comprehensive contract testing report."""
        violations = self.validate_contracts()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_interactions": len(self.interactions),
            "total_expectations": len(self.expectations),
            "violations_count": len(violations),
            "violations": violations,
            "pass_rate": (len(self.interactions) - len(violations))
            / max(len(self.interactions), 1)
            * 100,
            "interactions": [asdict(interaction) for interaction in self.interactions],
            "expectations": [asdict(expectation) for expectation in self.expectations],
        }

    def save_report(self, file_path: Path) -> None:
        """Save contract testing report to file."""
        report = self.generate_contract_report()
        with open(file_path, "w") as f:
            json.dump(report, f, indent=2, default=str)


class JiraContractDefinitions:
    """Predefined contract expectations for Jira API."""

    @staticmethod
    def get_standard_expectations() -> List[ContractExpectation]:
        """Get standard Jira API contract expectations."""
        return [
            # Authentication endpoint
            ContractExpectation(
                method="GET",
                endpoint_pattern="/rest/api/2/myself",
                expected_headers={"Accept": "application/json"},
                response_type=ResponseType.SUCCESS,
                response_status=200,
                response_body={"accountId": "", "displayName": "", "emailAddress": ""},
                max_response_time_ms=3000,
            ),
            # Project retrieval
            ContractExpectation(
                method="GET",
                endpoint_pattern="/rest/api/2/project/",
                expected_headers={"Accept": "application/json"},
                response_type=ResponseType.SUCCESS,
                response_status=200,
                response_body={
                    "key": "",
                    "name": "",
                    "description": None,
                    "lead": None,
                    "components": [],
                },
                max_response_time_ms=5000,
            ),
            # Issues search
            ContractExpectation(
                method="GET",
                endpoint_pattern="/rest/api/2/search",
                expected_headers={"Accept": "application/json"},
                expected_params={"jql": None},
                response_type=ResponseType.SUCCESS,
                response_status=200,
                response_body={"issues": [], "total": 0, "maxResults": 50},
                max_response_time_ms=10000,
            ),
        ]


class ZephyrContractDefinitions:
    """Predefined contract expectations for Zephyr Scale API."""

    @staticmethod
    def get_standard_expectations() -> List[ContractExpectation]:
        """Get standard Zephyr Scale API contract expectations."""
        return [
            # Health check
            ContractExpectation(
                method="GET",
                endpoint_pattern="/rest/atm/1.0/healthcheck",
                expected_headers={"Authorization": "Bearer"},
                response_type=ResponseType.SUCCESS,
                response_status=200,
                max_response_time_ms=3000,
            ),
            # Test case search
            ContractExpectation(
                method="GET",
                endpoint_pattern="/rest/atm/1.0/testcase/search",
                expected_headers={"Authorization": "Bearer", "Accept": "application/json"},
                expected_params={"projectKey": "", "maxResults": 1000},
                response_type=ResponseType.SUCCESS,
                response_status=200,
                response_body={"values": []},
                max_response_time_ms=15000,
            ),
            # Test execution search
            ContractExpectation(
                method="GET",
                endpoint_pattern="/rest/atm/1.0/testrun",
                expected_headers={"Authorization": "Bearer", "Accept": "application/json"},
                response_type=ResponseType.SUCCESS,
                response_status=200,
                response_body={"values": []},
                max_response_time_ms=10000,
            ),
        ]


class QTestContractDefinitions:
    """Predefined contract expectations for qTest API."""

    @staticmethod
    def get_standard_expectations() -> List[ContractExpectation]:
        """Get standard qTest API contract expectations."""
        return [
            # User info
            ContractExpectation(
                method="GET",
                endpoint_pattern="/api/v3/users/me",
                expected_headers={"Authorization": "bearer"},
                response_type=ResponseType.SUCCESS,
                response_status=200,
                response_body={"id": 0, "username": "", "email": ""},
                max_response_time_ms=3000,
            ),
            # Projects list
            ContractExpectation(
                method="GET",
                endpoint_pattern="/api/v3/projects",
                expected_headers={"Authorization": "bearer", "Accept": "application/json"},
                response_type=ResponseType.SUCCESS,
                response_status=200,
                response_body=[],
                max_response_time_ms=5000,
            ),
            # Test cases in project
            ContractExpectation(
                method="GET",
                endpoint_pattern="/api/v3/projects/",
                expected_headers={"Authorization": "bearer", "Accept": "application/json"},
                response_type=ResponseType.SUCCESS,
                response_status=200,
                response_body={"items": [], "total": 0},
                max_response_time_ms=10000,
            ),
        ]


class ContractTestSuite:
    """Comprehensive contract testing suite for all external APIs."""

    def __init__(self):
        self.recorder = ContractTestRecorder()
        self._setup_standard_expectations()

    def _setup_standard_expectations(self) -> None:
        """Set up standard contract expectations for all APIs."""
        # Add Jira expectations
        for expectation in JiraContractDefinitions.get_standard_expectations():
            self.recorder.add_expectation(expectation)

        # Add Zephyr expectations
        for expectation in ZephyrContractDefinitions.get_standard_expectations():
            self.recorder.add_expectation(expectation)

        # Add qTest expectations
        for expectation in QTestContractDefinitions.get_standard_expectations():
            self.recorder.add_expectation(expectation)

    def mock_api_interaction(
        self,
        method: str,
        url: str,
        headers: Dict[str, str] = None,
        params: Dict[str, Any] = None,
        body: Dict[str, Any] = None,
        response_status: int = 200,
        response_body: Dict[str, Any] = None,
        response_time_ms: int = 100,
    ) -> None:
        """Mock an API interaction for contract testing."""

        headers = headers or {}
        auth_provided = any(key.lower() == "authorization" for key in headers.keys())

        interaction = ContractInteraction(
            timestamp=datetime.now(timezone.utc),
            method=method,
            url=url,
            headers=headers,
            params=params,
            body=body,
            response_status=response_status,
            response_headers={"Content-Type": "application/json"},
            response_body=response_body,
            response_time_ms=response_time_ms,
            auth_provided=auth_provided,
        )

        self.recorder.record_interaction(interaction)

    def validate_all_contracts(self) -> bool:
        """Validate all recorded interactions and return success status."""
        violations = self.recorder.validate_contracts()

        if violations:
            print(f"❌ Contract violations detected ({len(violations)}):")
            for violation in violations:
                print(f"  • {violation}")
            return False
        else:
            print(
                f"✅ All {len(self.recorder.interactions)} API interactions passed contract validation!"
            )
            return True

    def generate_contract_report(self, output_path: Path = None) -> Dict[str, Any]:
        """Generate and optionally save contract testing report."""
        report = self.recorder.generate_contract_report()

        if output_path:
            self.recorder.save_report(output_path)
            print(f"📄 Contract testing report saved to: {output_path}")

        return report


# Example usage for integration tests
def create_jira_interaction_example():
    """Example of how to use contract testing for Jira interactions."""
    suite = ContractTestSuite()

    # Mock a successful Jira authentication
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

    # Mock a project retrieval
    suite.mock_api_interaction(
        method="GET",
        url="https://example.atlassian.net/rest/api/2/project/TEST",
        headers={"Authorization": "Bearer token123", "Accept": "application/json"},
        response_status=200,
        response_body={
            "key": "TEST",
            "name": "Test Project",
            "description": "A test project",
            "lead": {"displayName": "Project Lead"},
            "components": [{"name": "Backend"}, {"name": "Frontend"}],
        },
        response_time_ms=300,
    )

    return suite


if __name__ == "__main__":
    # Demo contract testing
    print("🧪 Contract Testing Demo")
    print("=" * 30)

    suite = create_jira_interaction_example()
    success = suite.validate_all_contracts()

    if success:
        print("\n🎉 All contract tests passed!")
    else:
        print("\n❌ Contract violations detected!")

    # Generate report
    report = suite.generate_contract_report()
    print(f"\n📊 Contract Test Summary:")
    print(f"  - Total interactions: {report['total_interactions']}")
    print(f"  - Violations: {report['violations_count']}")
    print(f"  - Pass rate: {report['pass_rate']:.1f}%")
