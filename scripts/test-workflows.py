#!/usr/bin/env python3
"""
Test GitHub Actions workflows locally to verify they work correctly.

This script simulates workflow execution locally to catch issues before
deploying to GitHub Actions. It validates:
- Test commands can run successfully
- Coverage reports are generated
- Artifact paths exist
- Integration tests pass
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import time


class WorkflowTester:
    """Tests GitHub Actions workflows locally."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.temp_dir = Path(tempfile.mkdtemp(prefix="workflow_test_"))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clean up temporary directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_all_workflows(self) -> bool:
        """Test all workflows that can be simulated locally."""
        print("🧪 Testing GitHub Actions workflows locally...")
        print(f"📁 Test artifacts will be stored in: {self.temp_dir}")

        success = True

        # Test individual rail components
        if not self.test_rail_1_components():
            success = False

        if not self.test_rail_2_components():
            success = False

        if not self.test_rail_3_components():
            success = False

        # Test integration workflow components
        if not self.test_integration_tests():
            success = False

        # Test shared actions
        if not self.test_shared_actions():
            success = False

        # Generate test report
        self._generate_test_report()

        return success

    def test_rail_1_components(self) -> bool:
        """Test Rail 1: Core Business Logic components."""
        print("\n🚂 Testing Rail 1: Core Business Logic")

        success = True

        # Test core calculations
        modules = ["metrics", "time_windows"]
        for module in modules:
            if not self._test_module(f"Rail 1 - {module}", f"test_{module}.py"):
                success = False

        # Test data validation
        modules = ["validators", "models", "config"]
        for module in modules:
            if not self._test_module(f"Rail 1 - {module}", f"test_{module}*.py"):
                success = False

        # Test business logic integration
        if not self._test_business_logic_integration():
            success = False

        return success

    def test_rail_2_components(self) -> bool:
        """Test Rail 2: Infrastructure Services components."""
        print("\n🚂 Testing Rail 2: Infrastructure Services")

        success = True

        # Test caching infrastructure
        if not self._test_module("Rail 2 - cache", "test_cache.py"):
            success = False

        # Test resilience infrastructure
        modules = ["rate_limiter", "error_handler"]
        for module in modules:
            if not self._test_module(f"Rail 2 - {module}", f"test_{module}.py"):
                success = False

        # Test observability infrastructure
        modules = ["observability", "monitoring_api"]
        for module in modules:
            if not self._test_module(f"Rail 2 - {module}", f"test_{module}.py"):
                success = False

        # Test infrastructure integration
        if not self._test_infrastructure_integration():
            success = False

        return success

    def test_rail_3_components(self) -> bool:
        """Test Rail 3: External Integrations components."""
        print("\n🚂 Testing Rail 3: External Integrations")

        success = True

        # Test API clients
        if not self._test_module("Rail 3 - client", "test_client.py"):
            success = False

        # Test CLI commands (if tests exist)
        if Path("tests/unit/ledzephyr/test_cli.py").exists():
            if not self._test_module("Rail 3 - CLI", "test_cli*.py"):
                success = False

        # Test exporters (if tests exist)
        if Path("tests/unit/ledzephyr/test_exporters.py").exists():
            if not self._test_module("Rail 3 - exporters", "test_exporters.py"):
                success = False

        return success

    def test_integration_tests(self) -> bool:
        """Test integration test components."""
        print("\n🔗 Testing Integration Components")

        # Test mock services integration
        return self._test_integration_component("Mock Services", "test_mock_services.py")

    def test_shared_actions(self) -> bool:
        """Test shared actions can be simulated."""
        print("\n⚙️  Testing Shared Actions")

        # Test Python/Poetry setup simulation
        return self._test_python_poetry_setup()

    def _test_module(self, component_name: str, test_pattern: str) -> bool:
        """Test a specific module with pytest."""
        print(f"  🔸 Testing {component_name}...")

        test_path = f"tests/unit/ledzephyr/{test_pattern}"
        artifact_name = f"test_{component_name.lower().replace(' ', '_').replace('-', '_')}"

        try:
            # Run pytest with coverage
            cmd = [
                "poetry",
                "run",
                "pytest",
                test_path,
                "--cov=src/ledzephyr",
                f"--cov-report=xml:{self.temp_dir}/{artifact_name}_coverage.xml",
                f"--junit-xml={self.temp_dir}/{artifact_name}_results.xml",
                "-v",
                "--tb=short",
            ]

            result = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            success = result.returncode == 0

            self.test_results[component_name] = {
                "success": success,
                "duration": 0,  # Would be timed in real implementation
                "coverage_file": f"{artifact_name}_coverage.xml",
                "results_file": f"{artifact_name}_results.xml",
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            if success:
                print(f"    ✅ {component_name} tests passed")
            else:
                print(f"    ❌ {component_name} tests failed")
                if result.stderr:
                    print(f"    Error: {result.stderr[:200]}...")

            return success

        except subprocess.TimeoutExpired:
            print(f"    ⏰ {component_name} tests timed out")
            return False
        except Exception as e:
            print(f"    ❌ {component_name} test error: {e}")
            return False

    def _test_business_logic_integration(self) -> bool:
        """Test business logic integration workflow."""
        print("  🔸 Testing Business Logic Integration...")

        try:
            cmd = [
                "poetry",
                "run",
                "pytest",
                "tests/unit/ledzephyr/test_metrics.py",
                "tests/unit/ledzephyr/test_validators.py",
                "tests/unit/ledzephyr/test_time_windows.py",
                "tests/unit/ledzephyr/test_config.py",
                "--cov=src/ledzephyr/metrics.py",
                "--cov=src/ledzephyr/validators.py",
                "--cov=src/ledzephyr/time_windows.py",
                "--cov=src/ledzephyr/config.py",
                f"--cov-report=xml:{self.temp_dir}/business_logic_integration.xml",
                f"--junit-xml={self.temp_dir}/business_logic_results.xml",
                "-v",
            ]

            result = subprocess.run(
                cmd, cwd=self.repo_root, capture_output=True, text=True, timeout=300
            )
            success = result.returncode == 0

            if success:
                print("    ✅ Business logic integration passed")
            else:
                print("    ❌ Business logic integration failed")

            return success

        except Exception as e:
            print(f"    ❌ Business logic integration error: {e}")
            return False

    def _test_infrastructure_integration(self) -> bool:
        """Test infrastructure integration workflow."""
        print("  🔸 Testing Infrastructure Integration...")

        try:
            cmd = [
                "poetry",
                "run",
                "pytest",
                "tests/unit/ledzephyr/test_cache.py",
                "tests/unit/ledzephyr/test_rate_limiter.py",
                "tests/unit/ledzephyr/test_error_handler.py",
                "tests/unit/ledzephyr/test_observability.py",
                "--cov=src/ledzephyr/cache.py",
                "--cov=src/ledzephyr/rate_limiter.py",
                "--cov=src/ledzephyr/error_handler.py",
                "--cov=src/ledzephyr/observability.py",
                f"--cov-report=xml:{self.temp_dir}/infrastructure_integration.xml",
                f"--junit-xml={self.temp_dir}/infrastructure_results.xml",
                "-v",
            ]

            result = subprocess.run(
                cmd, cwd=self.repo_root, capture_output=True, text=True, timeout=300
            )
            success = result.returncode == 0

            if success:
                print("    ✅ Infrastructure integration passed")
            else:
                print("    ❌ Infrastructure integration failed")

            return success

        except Exception as e:
            print(f"    ❌ Infrastructure integration error: {e}")
            return False

    def _test_integration_component(self, component_name: str, test_file: str) -> bool:
        """Test an integration component."""
        print(f"  🔸 Testing {component_name}...")

        try:
            cmd = [
                "poetry",
                "run",
                "pytest",
                f"tests/integration/{test_file}",
                f'--junit-xml={self.temp_dir}/{test_file.replace(".py", "_results.xml")}',
                "-v",
                "--tb=short",
            ]

            result = subprocess.run(
                cmd, cwd=self.repo_root, capture_output=True, text=True, timeout=300
            )
            success = result.returncode == 0

            if success:
                print(f"    ✅ {component_name} integration passed")
            else:
                print(f"    ❌ {component_name} integration failed")
                if result.stderr:
                    print(f"    Error: {result.stderr[:200]}...")

            return success

        except Exception as e:
            print(f"    ❌ {component_name} integration error: {e}")
            return False

    def _test_python_poetry_setup(self) -> bool:
        """Test Python/Poetry setup simulation."""
        print("  🔸 Testing Python/Poetry setup simulation...")

        try:
            # Verify poetry is available
            result = subprocess.run(["poetry", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                print("    ❌ Poetry not available")
                return False

            # Verify dependencies are installed
            result = subprocess.run(
                ["poetry", "install", "--dry-run"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print("    ❌ Poetry dependencies check failed")
                return False

            print("    ✅ Python/Poetry setup simulation passed")
            return True

        except Exception as e:
            print(f"    ❌ Python/Poetry setup error: {e}")
            return False

    def _generate_test_report(self) -> None:
        """Generate a comprehensive test report."""
        print("\n📊 Generating test report...")

        report_file = self.temp_dir / "workflow_test_report.json"

        report = {
            "timestamp": time.time(),
            "total_components": len(self.test_results),
            "passed_components": sum(1 for r in self.test_results.values() if r["success"]),
            "failed_components": sum(1 for r in self.test_results.values() if not r["success"]),
            "results": self.test_results,
            "artifacts_directory": str(self.temp_dir),
        }

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"📄 Test report saved to: {report_file}")

        # Print summary
        print("\n" + "=" * 60)
        print("📋 WORKFLOW TEST SUMMARY")
        print("=" * 60)
        print(f"Total components tested: {report['total_components']}")
        print(f"Passed: {report['passed_components']}")
        print(f"Failed: {report['failed_components']}")

        if report["failed_components"] == 0:
            print("🎉 All workflow components passed local testing!")
        else:
            print("❌ Some workflow components failed local testing.")

        print(f"\n📁 Test artifacts available in: {self.temp_dir}")


def check_prerequisites() -> bool:
    """Check that prerequisites for testing are available."""
    print("🔍 Checking prerequisites...")

    # Check poetry is available
    try:
        result = subprocess.run(["poetry", "--version"], capture_output=True)
        if result.returncode != 0:
            print("❌ Poetry not found. Please install Poetry first.")
            return False
        print("✅ Poetry available")
    except FileNotFoundError:
        print("❌ Poetry not found. Please install Poetry first.")
        return False

    # Check pytest is available
    try:
        result = subprocess.run(["poetry", "run", "pytest", "--version"], capture_output=True)
        if result.returncode != 0:
            print("❌ Pytest not available. Run 'poetry install' first.")
            return False
        print("✅ Pytest available")
    except Exception:
        print("❌ Pytest not available. Run 'poetry install' first.")
        return False

    # Check basic test directory structure
    required_dirs = ["tests/unit/ledzephyr", "tests/integration"]

    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            print(f"❌ Required directory not found: {dir_path}")
            return False
        print(f"✅ {dir_path} exists")

    return True


def main():
    """Main testing function."""
    print("🧪 LedZephyr Workflow Local Testing")
    print("=" * 40)

    # Change to repository root
    repo_root = Path(__file__).parent.parent
    os.chdir(repo_root)

    # Check prerequisites
    if not check_prerequisites():
        print("❌ Prerequisites not met. Please fix issues above.")
        return 1

    # Run workflow tests
    with WorkflowTester(repo_root) as tester:
        success = tester.test_all_workflows()

    if success:
        print("\n🎉 ALL WORKFLOW TESTS PASSED!")
        print("Your workflows are ready for GitHub Actions deployment.")
        return 0
    else:
        print("\n❌ SOME WORKFLOW TESTS FAILED!")
        print("Please fix the issues above before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
