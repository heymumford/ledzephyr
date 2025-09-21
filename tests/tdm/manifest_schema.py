"""
Test Data Management (TDM) manifest schema and validator.
"""

import hashlib
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DataSensitivity(str, Enum):
    """Data sensitivity levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class MaskingStrategy(str, Enum):
    """Masking strategies for sensitive data."""

    NONE = "none"
    TOKENIZE = "tokenize"  # Replace with token
    REDACT = "redact"  # Remove completely
    HASH = "hash"  # One-way hash
    PARTIAL = "partial"  # Show partial (e.g., ***1234)
    SYNTHETIC = "synthetic"  # Replace with synthetic data


class TestDataSource(BaseModel):
    """Source of test data."""

    type: str = Field(..., description="Source type: api, file, generated")
    endpoint: str | None = Field(None, description="API endpoint if applicable")
    file_path: str | None = Field(None, description="File path if applicable")
    generator: str | None = Field(None, description="Generator function if applicable")
    version: str = Field(..., description="Version of the data source")


class DataField(BaseModel):
    """Definition of a data field."""

    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Data type")
    sensitivity: DataSensitivity = Field(DataSensitivity.PUBLIC, description="Sensitivity level")
    masking: MaskingStrategy = Field(MaskingStrategy.NONE, description="Masking strategy")
    validation_rules: list[str] = Field(default_factory=list, description="Validation rules")
    golden_value: Any | None = Field(None, description="Expected golden value")


class TestDataSet(BaseModel):
    """A set of test data."""

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Dataset name")
    description: str = Field(..., description="Dataset description")
    source: TestDataSource = Field(..., description="Data source")
    fields: list[DataField] = Field(..., description="Field definitions")
    record_count: int = Field(..., description="Number of records")
    checksum: str | None = Field(None, description="Data checksum")
    tags: list[str] = Field(default_factory=list, description="Dataset tags")


class TestScenario(BaseModel):
    """Test scenario definition."""

    id: str = Field(..., description="Scenario ID")
    name: str = Field(..., description="Scenario name")
    description: str = Field(..., description="Scenario description")
    datasets: list[str] = Field(..., description="Required dataset IDs")
    preconditions: list[str] = Field(default_factory=list, description="Preconditions")
    expected_outcomes: list[str] = Field(..., description="Expected outcomes")
    quality_gates: list[str] = Field(default_factory=list, description="Quality gate checks")


class TDMManifest(BaseModel):
    """Test Data Management manifest."""

    version: str = Field("1.0.0", description="Manifest version")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    project: str = Field(..., description="Project identifier")
    environment: str = Field(..., description="Target environment")
    datasets: list[TestDataSet] = Field(..., description="Test data sets")
    scenarios: list[TestScenario] = Field(..., description="Test scenarios")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("datasets")
    def validate_unique_dataset_ids(cls, v):
        ids = [ds.id for ds in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Dataset IDs must be unique")
        return v

    @field_validator("scenarios")
    def validate_scenario_datasets(cls, v, values):
        if "datasets" in values.data:
            dataset_ids = {ds.id for ds in values.data["datasets"]}
            for scenario in v:
                for dataset_id in scenario.datasets:
                    if dataset_id not in dataset_ids:
                        raise ValueError(
                            f"Scenario {scenario.id} references unknown dataset {dataset_id}"
                        )
        return v


class ManifestValidator:
    """Validator for TDM manifests."""

    def __init__(self, manifest_path: str):
        self.manifest_path = Path(manifest_path)
        self.manifest: TDMManifest | None = None
        self.validation_errors: list[str] = []
        self.validation_warnings: list[str] = []

    def load(self) -> bool:
        """Load and parse manifest."""
        try:
            with open(self.manifest_path) as f:
                data = json.load(f)
            self.manifest = TDMManifest(**data)
            return True
        except Exception as e:
            self.validation_errors.append(f"Failed to load manifest: {e}")
            return False

    def validate_schema(self) -> bool:
        """Validate manifest schema."""
        if not self.manifest:
            self.validation_errors.append("Manifest not loaded")
            return False

        # Schema validation is done by Pydantic
        return True

    def validate_completeness(self) -> bool:
        """Validate data completeness."""
        if not self.manifest:
            return False

        complete = True

        # Check each dataset has data
        for dataset in self.manifest.datasets:
            if dataset.record_count == 0:
                self.validation_warnings.append(f"Dataset {dataset.id} has no records")

            # Check sensitive fields have masking
            for field in dataset.fields:
                if (
                    field.sensitivity != DataSensitivity.PUBLIC
                    and field.masking == MaskingStrategy.NONE
                ):
                    self.validation_errors.append(
                        f"Sensitive field {field.name} in dataset {dataset.id} has no masking"
                    )
                    complete = False

        # Check scenarios have expected outcomes
        for scenario in self.manifest.scenarios:
            if not scenario.expected_outcomes:
                self.validation_errors.append(f"Scenario {scenario.id} has no expected outcomes")
                complete = False

        return complete

    def validate_checksums(self, data_dir: str) -> bool:
        """Validate data checksums."""
        if not self.manifest:
            return False

        data_path = Path(data_dir)
        valid = True

        for dataset in self.manifest.datasets:
            if dataset.checksum:
                # Compute actual checksum
                file_path = data_path / f"{dataset.id}.json"
                if file_path.exists():
                    actual_checksum = self._compute_checksum(file_path)
                    if actual_checksum != dataset.checksum:
                        self.validation_errors.append(
                            f"Checksum mismatch for dataset {dataset.id}: expected {dataset.checksum}, got {actual_checksum}"
                        )
                        valid = False
                else:
                    self.validation_warnings.append(f"Data file not found for dataset {dataset.id}")

        return valid

    def _compute_checksum(self, file_path: Path) -> str:
        """Compute SHA256 checksum of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def validate_quality_gates(self) -> bool:
        """Validate quality gates."""
        if not self.manifest:
            return False

        gates_passed = True

        for scenario in self.manifest.scenarios:
            for gate in scenario.quality_gates:
                # Parse quality gate expressions
                if "coverage>" in gate:
                    required_coverage = float(gate.split(">")[1].strip("%"))
                    # This would integrate with actual coverage tools
                    self.validation_warnings.append(
                        f"Quality gate {gate} for scenario {scenario.id} requires external validation"
                    )
                elif "performance<" in gate:
                    max_time = float(gate.split("<")[1].strip("s"))
                    # This would integrate with performance tests
                    self.validation_warnings.append(
                        f"Quality gate {gate} for scenario {scenario.id} requires external validation"
                    )

        return gates_passed

    def get_report(self) -> dict[str, Any]:
        """Get validation report."""
        return {
            "valid": len(self.validation_errors) == 0,
            "errors": self.validation_errors,
            "warnings": self.validation_warnings,
            "summary": {
                "datasets": len(self.manifest.datasets) if self.manifest else 0,
                "scenarios": len(self.manifest.scenarios) if self.manifest else 0,
                "total_fields": (
                    sum(len(ds.fields) for ds in self.manifest.datasets) if self.manifest else 0
                ),
                "sensitive_fields": (
                    sum(
                        1
                        for ds in self.manifest.datasets
                        for f in ds.fields
                        if f.sensitivity != DataSensitivity.PUBLIC
                    )
                    if self.manifest
                    else 0
                ),
            },
        }


class ManifestGenerator:
    """Generate TDM manifests from existing test data."""

    @staticmethod
    def generate_from_stubs(output_path: str) -> TDMManifest:
        """Generate manifest from stub implementations."""

        # Define Jira dataset
        jira_dataset = TestDataSet(
            id="jira_issues",
            name="Jira Issues Dataset",
            description="Test issues from Jira stub",
            source=TestDataSource(type="api", endpoint="/rest/api/3/search", version="1.0.0"),
            fields=[
                DataField(name="id", type="string", sensitivity=DataSensitivity.INTERNAL),
                DataField(name="key", type="string", sensitivity=DataSensitivity.PUBLIC),
                DataField(name="summary", type="string", sensitivity=DataSensitivity.PUBLIC),
                DataField(
                    name="assignee.email",
                    type="string",
                    sensitivity=DataSensitivity.CONFIDENTIAL,
                    masking=MaskingStrategy.TOKENIZE,
                ),
                DataField(name="status", type="string", sensitivity=DataSensitivity.PUBLIC),
            ],
            record_count=75,
        )

        # Define Zephyr dataset
        zephyr_dataset = TestDataSet(
            id="zephyr_testcases",
            name="Zephyr Test Cases Dataset",
            description="Test cases from Zephyr stub",
            source=TestDataSource(type="api", endpoint="/testcases", version="1.0.0"),
            fields=[
                DataField(name="id", type="string", sensitivity=DataSensitivity.INTERNAL),
                DataField(name="key", type="string", sensitivity=DataSensitivity.PUBLIC),
                DataField(name="name", type="string", sensitivity=DataSensitivity.PUBLIC),
                DataField(name="status", type="string", sensitivity=DataSensitivity.PUBLIC),
                DataField(name="priority", type="string", sensitivity=DataSensitivity.PUBLIC),
            ],
            record_count=45,
        )

        # Define qTest dataset
        qtest_dataset = TestDataSet(
            id="qtest_testcases",
            name="qTest Test Cases Dataset",
            description="Test cases from qTest stub",
            source=TestDataSource(
                type="api", endpoint="/api/v3/projects/{projectId}/test-cases", version="1.0.0"
            ),
            fields=[
                DataField(name="id", type="integer", sensitivity=DataSensitivity.INTERNAL),
                DataField(name="name", type="string", sensitivity=DataSensitivity.PUBLIC),
                DataField(name="description", type="string", sensitivity=DataSensitivity.PUBLIC),
                DataField(
                    name="assigned_to",
                    type="string",
                    sensitivity=DataSensitivity.CONFIDENTIAL,
                    masking=MaskingStrategy.REDACT,
                ),
            ],
            record_count=150,
        )

        # Define test scenarios
        integration_scenario = TestScenario(
            id="integration_happy_path",
            name="Integration Happy Path",
            description="Test successful integration with all three vendors",
            datasets=["jira_issues", "zephyr_testcases", "qtest_testcases"],
            preconditions=["All APIs accessible", "Valid authentication"],
            expected_outcomes=[
                "All data retrieved successfully",
                "Pagination works correctly",
                "Data transformations applied",
            ],
            quality_gates=["coverage>80%", "performance<2s"],
        )

        pagination_scenario = TestScenario(
            id="pagination_test",
            name="Pagination Test",
            description="Test pagination across all vendors",
            datasets=["jira_issues", "zephyr_testcases", "qtest_testcases"],
            preconditions=["Datasets have multiple pages"],
            expected_outcomes=[
                "All pages retrieved",
                "No duplicate records",
                "Correct total count",
            ],
            quality_gates=["performance<5s"],
        )

        # Create manifest
        manifest = TDMManifest(
            project="ledzephyr",
            environment="test",
            datasets=[jira_dataset, zephyr_dataset, qtest_dataset],
            scenarios=[integration_scenario, pagination_scenario],
            metadata={
                "generated_by": "ManifestGenerator",
                "test_doubles": ["stub", "fake", "spy"],
                "vcr_enabled": True,
            },
        )

        # Save manifest
        with open(output_path, "w") as f:
            json.dump(manifest.model_dump(), f, indent=2, default=str)

        return manifest
