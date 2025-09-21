"""End-to-end tests using manifest-driven test data."""

import hashlib
import json
from datetime import UTC
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from tdm.tools.validate_manifest import validate_manifest

from ledzephyr.client import APIClient
from ledzephyr.config import Config
from ledzephyr.metrics import MetricsCalculator


class TestManifestReplay:
    """End-to-end tests using TDM manifests."""

    def test_validate_demo_manifest(self):
        """Test that our demo manifest is valid."""
        manifest_path = (
            Path(__file__).parent.parent.parent
            / "testdata"
            / "manifests"
            / "demo_project_2025q2.yaml"
        )

        # This should not raise an exception
        is_valid = validate_manifest(str(manifest_path))
        assert is_valid

    def test_manifest_driven_e2e_stub_mode(self, tmp_path):
        """Test full Pull→Math→Print pipeline using manifest with stubs."""
        # Load the manifest
        manifest_path = (
            Path(__file__).parent.parent.parent
            / "testdata"
            / "manifests"
            / "demo_project_2025q2.yaml"
        )
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        # Setup test configuration
        config = Config(
            jira_url="https://test.atlassian.net",
            jira_username="test@example.com",
            jira_api_token="test_token",
            zephyr_token="zephyr_test_token",
            qtest_url="https://test.qtestnet.com",
            qtest_token="qtest_test_token",
        )

        # Create output file
        output_file = tmp_path / "e2e_result.json"

        # Mock the API responses based on manifest sources
        with patch("ledzephyr.client.APIClient._make_request") as mock_request:
            # Setup responses for different API calls
            def mock_response_factory(method, url, **kwargs):
                mock_resp = Mock()
                mock_resp.status_code = 200

                if "/project/" in url:
                    # Jira project response
                    mock_resp.json.return_value = {
                        "key": "DEMO",
                        "name": "Demo Project",
                        "components": [{"name": "Frontend"}, {"name": "Backend"}],
                    }
                elif "testcase/search" in url:
                    # Zephyr tests response (stub preset: mixed_execution_status)
                    mock_resp.json.return_value = {
                        "values": [
                            {
                                "id": "Z-1",
                                "key": "Z-1",
                                "name": "Stubbed Zephyr Test",
                                "component": "Frontend",
                                "labels": ["ui"],
                                "owner": {"displayName": "alice@example.com"},
                                "createdOn": "2025-06-25T10:00:00Z",
                                "updatedOn": "2025-06-30T15:30:00Z",
                                "status": "Done",
                            }
                        ]
                    }
                elif "/projects" in url and "/test-cases" not in url:
                    # qTest projects response
                    mock_resp.json.return_value = [{"id": 12345, "name": "DEMO"}]
                elif "/test-cases" in url:
                    # qTest test cases response (fake config: 150 tests)
                    mock_resp.json.return_value = {
                        "items": [
                            {
                                "id": 1001,
                                "name": "Fake qTest Test",
                                "created_date": "2025-06-26T11:00:00Z",
                                "last_modified_date": "2025-06-30T17:00:00Z",
                                "status": "Active",
                                "tags": ["api"],
                            }
                        ]
                    }
                else:
                    # Default empty response
                    mock_resp.json.return_value = {}

                return mock_resp

            mock_request.side_effect = mock_response_factory

            # Run the Pull→Math→Print pipeline
            client = APIClient(config)
            calculator = MetricsCalculator(client)

            # Pull & Math
            metrics = calculator.calculate_metrics(
                manifest["dataset_id"].split("-")[0].upper(),  # "DEMO" from "demo-project-q2-2025"
                "7d",
            )

            # Print (to JSON)
            result_data = {
                "manifest_id": manifest["dataset_id"],
                "as_of": manifest["as_of"],
                "metrics": metrics.model_dump(),
            }

            with open(output_file, "w") as f:
                json.dump(result_data, f, indent=2, default=str)

        # Verify output exists and has expected structure
        assert output_file.exists()

        with open(output_file) as f:
            result = json.load(f)

        assert "manifest_id" in result
        assert "metrics" in result
        assert result["manifest_id"] == manifest["dataset_id"]

        # Verify metrics structure
        metrics_data = result["metrics"]
        assert "project_key" in metrics_data
        assert "total_tests" in metrics_data
        assert "adoption_ratio" in metrics_data

    def test_manifest_checksum_validation(self, tmp_path):
        """Test that output checksum validation works."""
        # Create a simple test output
        test_output = {"test": "data", "numbers": [1, 2, 3], "nested": {"key": "value"}}

        output_file = tmp_path / "test_output.json"
        with open(output_file, "w") as f:
            json.dump(test_output, f, sort_keys=True)

        # Calculate actual checksum
        with open(output_file, "rb") as f:
            actual_checksum = hashlib.sha256(f.read()).hexdigest()

        # Create manifest with expected checksum
        manifest = {
            "dataset_id": "test-checksum",
            "as_of": "2025-06-30T23:59:59Z",
            "sources": {"jira": {"mode": "stub", "preset": "basic_project"}},
            "quality_gates": {"expected_checksum": actual_checksum},
        }

        manifest_file = tmp_path / "test_manifest.yaml"
        with open(manifest_file, "w") as f:
            yaml.dump(manifest, f)

        # Validate manifest (should pass)
        assert validate_manifest(str(manifest_file))

        # Test checksum verification
        with open(output_file, "rb") as f:
            file_checksum = hashlib.sha256(f.read()).hexdigest()

        assert file_checksum == manifest["quality_gates"]["expected_checksum"]

    def test_tdm_masking_simulation(self):
        """Test TDM masking rules simulation."""
        # Simulate deterministic tokenization
        import hashlib

        # Mock environment variable
        test_salt = "test_salt_for_deterministic_masking"

        # Test data to mask
        sensitive_data = ["user123@example.com", "test_case_id_456", "project_key_789"]

        # Apply deterministic masking
        masked_data = []
        for item in sensitive_data:
            # Simulate deterministic_tokenize operation
            hash_input = f"{test_salt}_{item}".encode()
            hashed = hashlib.sha256(hash_input).hexdigest()

            # Convert to base32-like token (first 16 chars for readability)
            token = hashed[:16].upper()
            masked_data.append(token)

        # Verify properties
        assert len(masked_data) == len(sensitive_data)
        assert all(len(token) == 16 for token in masked_data)
        assert len(set(masked_data)) == len(masked_data)  # All unique

        # Verify deterministic property - same input produces same output
        second_pass = []
        for item in sensitive_data:
            hash_input = f"{test_salt}_{item}".encode()
            hashed = hashlib.sha256(hash_input).hexdigest()
            token = hashed[:16].upper()
            second_pass.append(token)

        assert masked_data == second_pass  # Deterministic


class TestTDMQualityGates:
    """Test TDM quality gates and validation."""

    def test_schema_compliance_gate(self):
        """Test schema compliance quality gate."""
        from jsonschema import ValidationError, validate

        # Valid data
        valid_metrics = {
            "project_key": "TEST",
            "time_window": "7d",
            "total_tests": 100,
            "adoption_ratio": 0.75,
        }

        # Simple schema
        schema = {
            "type": "object",
            "required": ["project_key", "time_window", "total_tests"],
            "properties": {
                "project_key": {"type": "string"},
                "time_window": {"type": "string"},
                "total_tests": {"type": "integer", "minimum": 0},
                "adoption_ratio": {"type": "number", "minimum": 0, "maximum": 1},
            },
        }

        # Should pass
        validate(valid_metrics, schema)

        # Invalid data should fail
        invalid_metrics = {
            "project_key": "TEST",
            "time_window": "7d",
            "total_tests": -5,  # Invalid: negative
            "adoption_ratio": 1.5,  # Invalid: > 1
        }

        with pytest.raises(ValidationError):
            validate(invalid_metrics, schema)

    def test_completeness_quality_gate(self):
        """Test data completeness quality gate."""
        # Test data with some null values
        test_data = [
            {"name": "test1", "value": 100, "category": "A"},
            {"name": "test2", "value": None, "category": "B"},
            {"name": "test3", "value": 200, "category": None},
            {"name": "test4", "value": 150, "category": "A"},
        ]

        # Calculate completeness for each field
        total_records = len(test_data)

        name_completeness = sum(1 for item in test_data if item["name"] is not None) / total_records
        value_completeness = (
            sum(1 for item in test_data if item["value"] is not None) / total_records
        )
        category_completeness = (
            sum(1 for item in test_data if item["category"] is not None) / total_records
        )

        assert name_completeness == 1.0  # 100% complete
        assert value_completeness == 0.75  # 75% complete
        assert category_completeness == 0.75  # 75% complete

        # Quality gate: minimum 80% completeness
        min_completeness = 0.8
        assert name_completeness >= min_completeness  # Pass
        assert value_completeness < min_completeness  # Fail
        assert category_completeness < min_completeness  # Fail

    def test_time_consistency_gate(self):
        """Test time consistency across data sources."""
        from datetime import datetime

        # Simulate data from different sources with timestamps
        jira_data = [
            {"id": "J-1", "updated": "2025-06-30T14:00:00Z"},
            {"id": "J-2", "updated": "2025-06-30T15:00:00Z"},
        ]

        zephyr_data = [
            {"id": "Z-1", "updated": "2025-06-30T14:30:00Z"},
            {"id": "Z-2", "updated": "2025-06-30T15:30:00Z"},
        ]

        # Parse timestamps
        def parse_timestamp(ts_str):
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

        jira_times = [parse_timestamp(item["updated"]) for item in jira_data]
        zephyr_times = [parse_timestamp(item["updated"]) for item in zephyr_data]

        # Check that all timestamps are within the expected time window
        test_window_start = datetime(2025, 6, 30, 12, 0, 0, tzinfo=UTC)
        test_window_end = datetime(2025, 6, 30, 18, 0, 0, tzinfo=UTC)

        all_times = jira_times + zephyr_times
        times_in_window = [test_window_start <= ts <= test_window_end for ts in all_times]

        assert all(times_in_window)  # All timestamps within expected window
