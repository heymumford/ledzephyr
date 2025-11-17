#!/usr/bin/env python3
"""Master test runner for LedZephyr.

Executes tests in the proper order following the test pyramid:
1. Unit Tests - Fast, isolated function tests
2. Contract Tests - API interface health checks
3. Integration Tests - Component interaction tests
4. E2E Tests - Full system tests (manual, see test_e2e.md)
"""

import sys
from typing import Tuple

# Import test modules
from test_contract import run_contract_tests
from test_integration import run_integration_tests
from test_unit import run_unit_tests


def run_test_suite() -> Tuple[bool, dict]:
    """Run complete test suite in proper order.

    Returns:
        Tuple of (success, results_dict)
    """
    results = {"unit": False, "contract": False, "integration": False}

    print("\n" + "=" * 70)
    print("LedZephyr Test Suite")
    print("=" * 70)
    print("\nTest Execution Order: Unit → Contract → Integration → E2E")
    print("=" * 70 + "\n")

    # Phase 1: Unit Tests
    print("PHASE 1: UNIT TESTS")
    print("-" * 70)
    try:
        run_unit_tests()
        results["unit"] = True
        print("\n✓ Unit tests PASSED\n")
    except SystemExit:
        print("\n✗ Unit tests FAILED - stopping test execution")
        print("Fix unit tests before proceeding to contract/integration tests.\n")
        return False, results

    # Phase 2: Contract Tests
    print("\nPHASE 2: CONTRACT TESTS")
    print("-" * 70)
    try:
        run_contract_tests()
        results["contract"] = True
        print("\n✓ Contract tests PASSED\n")
    except SystemExit:
        print("\n✗ Contract tests FAILED - stopping test execution")
        print("Fix contract tests before proceeding to integration tests.\n")
        return False, results

    # Phase 3: Integration Tests
    print("\nPHASE 3: INTEGRATION TESTS")
    print("-" * 70)
    try:
        run_integration_tests()
        results["integration"] = True
        print("\n✓ Integration tests PASSED\n")
    except SystemExit:
        print("\n✗ Integration tests FAILED\n")
        return False, results

    # Phase 4: E2E Tests (manual)
    print("\nPHASE 4: E2E TESTS")
    print("-" * 70)
    print("⚠ E2E tests require manual execution with real API credentials")
    print("See tests/test_e2e.md for instructions\n")

    return True, results


def print_summary(success: bool, results: dict) -> None:
    """Print test execution summary."""
    print("\n" + "=" * 70)
    print("TEST SUITE SUMMARY")
    print("=" * 70)

    status_icon = "✓" if results["unit"] else "✗"
    print(
        f"{status_icon} Unit Tests:        {'PASSED' if results['unit'] else 'FAILED'}"
    )

    status_icon = "✓" if results["contract"] else "✗"
    status = "PASSED" if results["contract"] else "FAILED"
    print(f"{status_icon} Contract Tests:    {status}")

    status_icon = "✓" if results["integration"] else "✗"
    status = "PASSED" if results["integration"] else "FAILED"
    print(f"{status_icon} Integration Tests: {status}")

    print("⚠ E2E Tests:         MANUAL (see test_e2e.md)")

    print("=" * 70)

    if success:
        print("✓ ALL AUTOMATED TESTS PASSED")
        print("\nYour changes are ready for:")
        print("  • Code review")
        print("  • Manual E2E testing")
        print("  • Deployment to staging")
    else:
        print("✗ SOME TESTS FAILED")
        print("\nPlease fix failing tests before proceeding.")

    print("=" * 70 + "\n")


def main() -> None:
    """Main entry point for test runner."""
    success, results = run_test_suite()
    print_summary(success, results)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
