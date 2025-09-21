#!/usr/bin/env python3
"""
Validate GitHub Actions workflow files for syntax and configuration issues.

This script validates the parallel testing architecture workflows to ensure:
- YAML syntax is correct
- Required actions and steps are present
- Dependencies between jobs are properly configured
- Matrix strategies are valid
- Artifact uploads/downloads are consistent
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Any, Set
import subprocess


class WorkflowValidator:
    """Validates GitHub Actions workflow files."""

    def __init__(self, workflows_dir: Path):
        self.workflows_dir = workflows_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.workflows: Dict[str, Dict[str, Any]] = {}

    def validate_all_workflows(self) -> bool:
        """Validate all workflow files in the workflows directory."""
        workflow_files = list(self.workflows_dir.glob("*.yml"))

        if not workflow_files:
            self.errors.append("No workflow files found in .github/workflows/")
            return False

        print(f"🔍 Validating {len(workflow_files)} workflow files...")

        # Load and parse all workflows
        for workflow_file in workflow_files:
            if not self._load_workflow(workflow_file):
                continue

        # Validate individual workflows
        for name, workflow in self.workflows.items():
            self._validate_workflow_structure(name, workflow)
            self._validate_job_dependencies(name, workflow)
            self._validate_matrix_strategies(name, workflow)
            self._validate_artifacts(name, workflow)

        # Validate cross-workflow consistency
        self._validate_cross_workflow_consistency()

        # Report results
        self._report_results()

        return len(self.errors) == 0

    def _load_workflow(self, workflow_file: Path) -> bool:
        """Load and parse a workflow YAML file."""
        try:
            with open(workflow_file, "r") as f:
                workflow_content = yaml.safe_load(f)

            if workflow_content is None:
                self.errors.append(f"{workflow_file.name}: Empty workflow file")
                return False

            self.workflows[workflow_file.name] = workflow_content
            print(f"✅ Loaded {workflow_file.name}")
            return True

        except yaml.YAMLError as e:
            self.errors.append(f"{workflow_file.name}: YAML syntax error - {e}")
            return False
        except Exception as e:
            self.errors.append(f"{workflow_file.name}: Failed to load - {e}")
            return False

    def _validate_workflow_structure(self, name: str, workflow: Dict[str, Any]) -> None:
        """Validate basic workflow structure."""
        required_fields = ["name", "on", "jobs"]

        for field in required_fields:
            if field not in workflow:
                self.errors.append(f"{name}: Missing required field '{field}'")

        # Validate 'on' triggers
        if "on" in workflow:
            triggers = workflow["on"]
            if isinstance(triggers, dict):
                valid_triggers = {"push", "pull_request", "workflow_dispatch", "schedule"}
                for trigger in triggers.keys():
                    if trigger not in valid_triggers:
                        self.warnings.append(f"{name}: Unknown trigger '{trigger}'")

    def _validate_job_dependencies(self, name: str, workflow: Dict[str, Any]) -> None:
        """Validate job dependencies and needs relationships."""
        if "jobs" not in workflow:
            return

        jobs = workflow["jobs"]
        job_names = set(jobs.keys())

        for job_name, job_config in jobs.items():
            if "needs" in job_config:
                needs = job_config["needs"]
                if isinstance(needs, str):
                    needs = [needs]
                elif not isinstance(needs, list):
                    self.errors.append(f"{name}:{job_name}: 'needs' must be string or list")
                    continue

                # Check that all needed jobs exist
                for needed_job in needs:
                    if needed_job not in job_names:
                        self.errors.append(
                            f"{name}:{job_name}: Depends on non-existent job '{needed_job}'"
                        )

    def _validate_matrix_strategies(self, name: str, workflow: Dict[str, Any]) -> None:
        """Validate matrix strategies for parallel execution."""
        if "jobs" not in workflow:
            return

        for job_name, job_config in workflow["jobs"].items():
            if "strategy" in job_config:
                strategy = job_config["strategy"]

                if "matrix" in strategy:
                    matrix = strategy["matrix"]

                    # Validate matrix dimensions
                    if not isinstance(matrix, dict):
                        self.errors.append(f"{name}:{job_name}: Matrix must be a dictionary")
                        continue

                    # Check for reasonable matrix sizes
                    total_combinations = 1
                    for key, values in matrix.items():
                        if isinstance(values, list):
                            total_combinations *= len(values)

                    if total_combinations > 50:
                        self.warnings.append(
                            f"{name}:{job_name}: Large matrix ({total_combinations} combinations)"
                        )

    def _validate_artifacts(self, name: str, workflow: Dict[str, Any]) -> None:
        """Validate artifact upload/download consistency."""
        if "jobs" not in workflow:
            return

        uploaded_artifacts: Set[str] = set()
        downloaded_artifacts: Set[str] = set()

        for job_name, job_config in workflow["jobs"].items():
            if "steps" not in job_config:
                continue

            for step in job_config["steps"]:
                if not isinstance(step, dict):
                    continue

                # Check artifact uploads
                if step.get("uses") == "actions/upload-artifact@v3":
                    if "with" in step and "name" in step["with"]:
                        uploaded_artifacts.add(step["with"]["name"])

                # Check artifact downloads
                elif step.get("uses") == "actions/download-artifact@v3":
                    if "with" in step and "name" in step["with"]:
                        downloaded_artifacts.add(step["with"]["name"])

        # Check for orphaned downloads
        orphaned = downloaded_artifacts - uploaded_artifacts
        for artifact in orphaned:
            self.warnings.append(
                f"{name}: Downloads artifact '{artifact}' that may not be uploaded"
            )

    def _validate_cross_workflow_consistency(self) -> None:
        """Validate consistency across workflows."""
        # Check for consistent Python versions
        python_versions = {}
        poetry_versions = {}

        for name, workflow in self.workflows.items():
            env = workflow.get("env", {})

            if "PYTHON_VERSION" in env:
                python_versions[name] = env["PYTHON_VERSION"]
            if "POETRY_VERSION" in env:
                poetry_versions[name] = env["POETRY_VERSION"]

        # Warn about version inconsistencies
        unique_python = set(python_versions.values())
        if len(unique_python) > 1:
            self.warnings.append(f"Inconsistent Python versions: {python_versions}")

        unique_poetry = set(poetry_versions.values())
        if len(unique_poetry) > 1:
            self.warnings.append(f"Inconsistent Poetry versions: {poetry_versions}")

        # Check for required shared action
        shared_action_used = False
        for name, workflow in self.workflows.items():
            if "jobs" in workflow:
                for job_name, job_config in workflow["jobs"].items():
                    if "steps" in job_config:
                        for step in job_config["steps"]:
                            if (
                                isinstance(step, dict)
                                and step.get("uses") == "./.github/actions/setup-python-poetry"
                            ):
                                shared_action_used = True
                                break

        if not shared_action_used:
            self.warnings.append(
                "Shared action './.github/actions/setup-python-poetry' not used in any workflow"
            )

    def _report_results(self) -> None:
        """Report validation results."""
        print("\n" + "=" * 60)
        print("🔍 WORKFLOW VALIDATION RESULTS")
        print("=" * 60)

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")

        if not self.errors and not self.warnings:
            print("\n✅ All workflows are valid!")
        elif not self.errors:
            print(f"\n✅ No errors found ({len(self.warnings)} warnings)")
        else:
            print(
                f"\n❌ Validation failed ({len(self.errors)} errors, {len(self.warnings)} warnings)"
            )


def validate_action_files(actions_dir: Path) -> bool:
    """Validate shared action files."""
    print(f"\n🔍 Validating shared actions in {actions_dir}...")

    action_files = list(actions_dir.glob("**/action.yml"))

    if not action_files:
        print("⚠️  No action.yml files found")
        return True

    errors = []

    for action_file in action_files:
        try:
            with open(action_file, "r") as f:
                action_content = yaml.safe_load(f)

            required_fields = ["name", "description", "runs"]
            for field in required_fields:
                if field not in action_content:
                    errors.append(
                        f"{action_file.relative_to(actions_dir)}: Missing required field '{field}'"
                    )

            print(f"✅ Validated {action_file.relative_to(actions_dir)}")

        except Exception as e:
            errors.append(f"{action_file.relative_to(actions_dir)}: {e}")

    if errors:
        print(f"\n❌ Action validation errors:")
        for error in errors:
            print(f"  • {error}")
        return False
    else:
        print("✅ All actions are valid!")
        return True


def validate_required_files() -> bool:
    """Validate that required files exist."""
    print("\n🔍 Checking required files...")

    required_files = [
        ".github/workflows/orchestrator.yml",  # Main orchestrator (may be named differently)
        ".github/workflows/coordinator.yml",  # Coordinator agent
        ".github/workflows/github-ai-assessment.yml",
        ".github/actions/setup-python-poetry/action.yml",
        "tests/integration/test_mock_services.py",
    ]

    # Optional files that enhance the architecture
    optional_files = [
        ".github/workflows/rail-1-core-business-logic.yml",
        ".github/workflows/rail-2-infrastructure-services.yml",
        ".github/workflows/rail-3-external-integrations.yml",
        ".github/workflows/orchestrator-master.yml",
        ".github/workflows/coordinator-agent.yml",
    ]

    missing_files = []

    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path}")

    if missing_files:
        print(f"\n❌ Missing required files:")
        for file_path in missing_files:
            print(f"  • {file_path}")
        success = False
    else:
        print("✅ All required files present!")
        success = True

    # Check optional files
    print("\n🔍 Checking optional enhancement files...")
    missing_optional = []
    for file_path in optional_files:
        if not Path(file_path).exists():
            missing_optional.append(file_path)
        else:
            print(f"✅ {file_path}")

    if missing_optional:
        print(f"\n⚠️  Optional files not found (workflow features may be limited):")
        for file_path in missing_optional:
            print(f"  • {file_path}")

    return success


def main():
    """Main validation function."""
    print("🚀 LedZephyr Parallel GitHub Actions Validation")
    print("=" * 50)

    # Change to repository root
    repo_root = Path(__file__).parent.parent
    os.chdir(repo_root)

    success = True

    # Validate required files exist
    if not validate_required_files():
        success = False

    # Validate shared actions
    actions_dir = Path(".github/actions")
    if actions_dir.exists():
        if not validate_action_files(actions_dir):
            success = False
    else:
        print("⚠️  No .github/actions directory found")

    # Validate workflows
    workflows_dir = Path(".github/workflows")
    if workflows_dir.exists():
        validator = WorkflowValidator(workflows_dir)
        if not validator.validate_all_workflows():
            success = False
    else:
        print("❌ No .github/workflows directory found")
        success = False

    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("Your parallel GitHub Actions architecture is ready to deploy.")
        return 0
    else:
        print("❌ VALIDATION FAILED!")
        print("Please fix the issues above before deploying workflows.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
