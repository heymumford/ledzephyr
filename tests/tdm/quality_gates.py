"""
Quality gates for test data management.
"""

import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


class GateStatus(str, Enum):
    """Quality gate status."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class GateResult:
    """Result of a quality gate check."""

    name: str
    status: GateStatus
    message: str
    details: dict[str, Any]
    execution_time_ms: float


class QualityGate:
    """Base class for quality gates."""

    def __init__(self, name: str, threshold: Any):
        self.name = name
        self.threshold = threshold

    def check(self, context: dict[str, Any]) -> GateResult:
        """Check if the gate passes."""
        raise NotImplementedError


class SchemaCompleteness(QualityGate):
    """Check schema completeness."""

    def check(self, context: dict[str, Any]) -> GateResult:
        start_time = time.time()

        manifest = context.get("manifest")
        if not manifest:
            return GateResult(
                name=self.name,
                status=GateStatus.FAILED,
                message="No manifest provided",
                details={},
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # Check required fields
        total_fields = 0
        missing_fields = 0
        incomplete_datasets = []

        for dataset in manifest.get("datasets", []):
            for field in dataset.get("fields", []):
                total_fields += 1
                if not field.get("type"):
                    missing_fields += 1
                    incomplete_datasets.append(dataset.get("id"))

        completeness_pct = (
            ((total_fields - missing_fields) / total_fields * 100) if total_fields > 0 else 0
        )

        if completeness_pct >= self.threshold:
            status = GateStatus.PASSED
            message = f"Schema completeness {completeness_pct:.1f}% >= {self.threshold}%"
        else:
            status = GateStatus.FAILED
            message = f"Schema completeness {completeness_pct:.1f}% < {self.threshold}%"

        return GateResult(
            name=self.name,
            status=status,
            message=message,
            details={
                "completeness_percentage": completeness_pct,
                "total_fields": total_fields,
                "missing_fields": missing_fields,
                "incomplete_datasets": list(set(incomplete_datasets)),
            },
            execution_time_ms=(time.time() - start_time) * 1000,
        )


class DataCoverage(QualityGate):
    """Check test data coverage."""

    def check(self, context: dict[str, Any]) -> GateResult:
        start_time = time.time()

        manifest = context.get("manifest")
        test_results = context.get("test_results", {})

        if not manifest:
            return GateResult(
                name=self.name,
                status=GateStatus.FAILED,
                message="No manifest provided",
                details={},
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # Calculate coverage
        total_scenarios = len(manifest.get("scenarios", []))
        tested_scenarios = len(test_results.get("executed_scenarios", []))

        coverage_pct = (tested_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0

        if coverage_pct >= self.threshold:
            status = GateStatus.PASSED
            message = f"Data coverage {coverage_pct:.1f}% >= {self.threshold}%"
        else:
            status = GateStatus.FAILED
            message = f"Data coverage {coverage_pct:.1f}% < {self.threshold}%"

        return GateResult(
            name=self.name,
            status=status,
            message=message,
            details={
                "coverage_percentage": coverage_pct,
                "total_scenarios": total_scenarios,
                "tested_scenarios": tested_scenarios,
            },
            execution_time_ms=(time.time() - start_time) * 1000,
        )


class PerformanceGate(QualityGate):
    """Check performance requirements."""

    def check(self, context: dict[str, Any]) -> GateResult:
        start_time = time.time()

        test_results = context.get("test_results", {})
        execution_times = test_results.get("execution_times", [])

        if not execution_times:
            return GateResult(
                name=self.name,
                status=GateStatus.SKIPPED,
                message="No performance data available",
                details={},
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)

        if max_time <= self.threshold:
            status = GateStatus.PASSED
            message = f"Max execution time {max_time:.2f}s <= {self.threshold}s"
        else:
            status = GateStatus.FAILED
            message = f"Max execution time {max_time:.2f}s > {self.threshold}s"

        return GateResult(
            name=self.name,
            status=status,
            message=message,
            details={
                "avg_execution_time": avg_time,
                "max_execution_time": max_time,
                "min_execution_time": min(execution_times),
                "total_executions": len(execution_times),
            },
            execution_time_ms=(time.time() - start_time) * 1000,
        )


class SensitiveDataGate(QualityGate):
    """Check sensitive data is properly masked."""

    def check(self, context: dict[str, Any]) -> GateResult:
        start_time = time.time()

        manifest = context.get("manifest")
        data_samples = context.get("data_samples", [])

        if not manifest:
            return GateResult(
                name=self.name,
                status=GateStatus.FAILED,
                message="No manifest provided",
                details={},
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # Check sensitive fields
        sensitive_fields = []
        unmasked_fields = []

        for dataset in manifest.get("datasets", []):
            for field in dataset.get("fields", []):
                if field.get("sensitivity") not in ["public", None]:
                    sensitive_fields.append(field.get("name"))
                    if field.get("masking") in ["none", None]:
                        unmasked_fields.append(field.get("name"))

        # Check actual data for leaks
        potential_leaks = []
        patterns = [
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # Email
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # Phone
            r"\b\d{9}\b",  # SSN-like
        ]

        import re

        for sample in data_samples:
            for pattern in patterns:
                if re.search(pattern, str(sample)):
                    potential_leaks.append(pattern)

        if len(unmasked_fields) == 0 and len(potential_leaks) == 0:
            status = GateStatus.PASSED
            message = "All sensitive data properly masked"
        elif len(unmasked_fields) > 0:
            status = GateStatus.FAILED
            message = f"{len(unmasked_fields)} sensitive fields not masked"
        else:
            status = GateStatus.WARNING
            message = "Potential data leaks detected"

        return GateResult(
            name=self.name,
            status=status,
            message=message,
            details={
                "sensitive_fields": sensitive_fields,
                "unmasked_fields": unmasked_fields,
                "potential_leaks": list(set(potential_leaks)),
            },
            execution_time_ms=(time.time() - start_time) * 1000,
        )


class DeterminismGate(QualityGate):
    """Check data is deterministic across runs."""

    def check(self, context: dict[str, Any]) -> GateResult:
        start_time = time.time()

        checksums = context.get("checksums", [])

        if len(checksums) < 2:
            return GateResult(
                name=self.name,
                status=GateStatus.SKIPPED,
                message="Need at least 2 runs to verify determinism",
                details={},
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # Check if all checksums match
        unique_checksums = set(checksums)

        if len(unique_checksums) == 1:
            status = GateStatus.PASSED
            message = f"Data is deterministic across {len(checksums)} runs"
        else:
            status = GateStatus.FAILED
            message = f"Data varies across runs ({len(unique_checksums)} different checksums)"

        return GateResult(
            name=self.name,
            status=status,
            message=message,
            details={
                "total_runs": len(checksums),
                "unique_checksums": list(unique_checksums),
                "is_deterministic": len(unique_checksums) == 1,
            },
            execution_time_ms=(time.time() - start_time) * 1000,
        )


class QualityGateRunner:
    """Runner for quality gates."""

    def __init__(self):
        self.gates: list[QualityGate] = []
        self.results: list[GateResult] = []

    def add_gate(self, gate: QualityGate):
        """Add a quality gate."""
        self.gates.append(gate)

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run all quality gates."""
        self.results = []

        for gate in self.gates:
            result = gate.check(context)
            self.results.append(result)

        # Summarize results
        passed = sum(1 for r in self.results if r.status == GateStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == GateStatus.FAILED)
        warnings = sum(1 for r in self.results if r.status == GateStatus.WARNING)
        skipped = sum(1 for r in self.results if r.status == GateStatus.SKIPPED)

        overall_status = GateStatus.PASSED
        if failed > 0:
            overall_status = GateStatus.FAILED
        elif warnings > 0:
            overall_status = GateStatus.WARNING

        return {
            "overall_status": overall_status,
            "summary": {
                "total": len(self.results),
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "skipped": skipped,
            },
            "results": [
                {
                    "name": r.name,
                    "status": r.status,
                    "message": r.message,
                    "details": r.details,
                    "execution_time_ms": r.execution_time_ms,
                }
                for r in self.results
            ],
        }

    def save_report(self, filepath: str):
        """Save quality gate report."""
        report = self.run({})
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)


def create_default_gates() -> QualityGateRunner:
    """Create default quality gates."""
    runner = QualityGateRunner()

    # Add default gates
    runner.add_gate(SchemaCompleteness("schema_completeness", threshold=95))
    runner.add_gate(DataCoverage("data_coverage", threshold=80))
    runner.add_gate(PerformanceGate("performance", threshold=2.0))  # 2 seconds
    runner.add_gate(SensitiveDataGate("sensitive_data", threshold=None))
    runner.add_gate(DeterminismGate("determinism", threshold=None))

    return runner
