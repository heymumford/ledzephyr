"""
Gold Master Testing for Algorithm Calculations

Tests core algorithms against known good datasets to ensure consistent results.
This is the critical test suite for maintaining calculation accuracy.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from ledzephyr.metrics import MetricsCalculator
from ledzephyr.models import ProjectMetrics, TestCaseModel


class TestGoldMasterAlgorithms:
    """Test algorithms against gold master datasets."""

    @pytest.fixture
    def fixtures_path(self) -> Path:
        """Path to test fixtures directory."""
        return Path(__file__).parent.parent.parent / "testdata" / "fixtures"

    @pytest.fixture
    def calculator(self) -> MetricsCalculator:
        """Metrics calculator instance."""
        return MetricsCalculator()

    def load_test_data(
        self, fixtures_path: Path, dataset_name: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Load input and expected output for a dataset."""
        input_file = fixtures_path / f"math_input_{dataset_name}.json"
        output_file = fixtures_path / f"math_output_{dataset_name}.json"

        with open(input_file) as f:
            input_data = json.load(f)

        with open(output_file) as f:
            expected_output = json.load(f)

        return input_data, expected_output

    def convert_to_test_cases(self, input_data: dict[str, Any]) -> list[TestCaseModel]:
        """Convert input JSON to TestCase objects."""
        test_cases = []

        for case_data in input_data.get("test_cases", []):
            test_case = TestCaseModel(
                id=case_data["id"],
                key=case_data["key"],
                summary=case_data["summary"],
                project_key=case_data["project_key"],
                component=case_data.get("component"),
                labels=case_data.get("labels", []),
                assignee=case_data.get("assignee"),
                source_system=case_data["source_system"],
                created=datetime.fromisoformat(case_data["created"].replace("Z", "+00:00")),
                updated=datetime.fromisoformat(case_data["updated"].replace("Z", "+00:00")),
                status=case_data["status"],
                last_execution=(
                    datetime.fromisoformat(case_data["last_execution"].replace("Z", "+00:00"))
                    if case_data.get("last_execution")
                    else None
                ),
                execution_status=case_data.get("execution_status"),
            )
            test_cases.append(test_case)

        return test_cases

    def assert_metrics_match(
        self, actual: ProjectMetrics, expected: dict[str, Any], tolerance: float = 0.001
    ):
        """Assert that calculated metrics match expected values within tolerance."""

        # Basic metrics
        assert actual.project_key == expected["project_key"]
        assert actual.time_window == expected["time_window"]
        assert actual.total_tests == expected["total_tests"]
        assert actual.zephyr_tests == expected["zephyr_tests"]
        assert actual.qtest_tests == expected["qtest_tests"]
        assert actual.active_users == expected["active_users"]

        # Float comparisons with tolerance
        assert (
            abs(actual.adoption_ratio - expected["adoption_ratio"]) <= tolerance
        ), f"adoption_ratio: expected {expected['adoption_ratio']}, got {actual.adoption_ratio}"

        assert (
            abs(actual.coverage_parity - expected["coverage_parity"]) <= tolerance
        ), f"coverage_parity: expected {expected['coverage_parity']}, got {actual.coverage_parity}"

        assert (
            abs(actual.defect_link_rate - expected["defect_link_rate"]) <= tolerance
        ), f"defect_link_rate: expected {expected['defect_link_rate']}, got {actual.defect_link_rate}"

        # Team metrics
        expected_teams = expected.get("team_metrics", {})
        assert len(actual.team_metrics) == len(
            expected_teams
        ), f"Team count mismatch: expected {len(expected_teams)}, got {len(actual.team_metrics)}"

        for team_name, expected_team in expected_teams.items():
            assert team_name in actual.team_metrics, f"Missing team: {team_name}"

            actual_team = actual.team_metrics[team_name]
            assert actual_team.team_name == expected_team["team_name"]
            assert actual_team.total_tests == expected_team["total_tests"]
            assert actual_team.zephyr_tests == expected_team["zephyr_tests"]
            assert actual_team.qtest_tests == expected_team["qtest_tests"]
            assert actual_team.active_users == expected_team["active_users"]
            assert actual_team.team_source.value == expected_team["teams_source"]

            assert (
                abs(actual_team.adoption_ratio - expected_team["adoption_ratio"]) <= tolerance
            ), f"Team {team_name} adoption_ratio: expected {expected_team['adoption_ratio']}, got {actual_team.adoption_ratio}"

    @pytest.mark.unit
    def test_basic_dataset_algorithms(self, fixtures_path: Path, calculator: MetricsCalculator):
        """Test algorithms against basic dataset."""
        input_data, expected_output = self.load_test_data(fixtures_path, "basic")
        test_cases = self.convert_to_test_cases(input_data)

        # Calculate metrics
        actual_metrics = calculator.calculate_project_metrics(
            test_cases=test_cases,
            project_key=input_data["project_key"],
            time_window=input_data["time_window"],
        )

        # Assert against gold master
        self.assert_metrics_match(actual_metrics, expected_output)

    @pytest.mark.unit
    def test_edge_cases_algorithms(self, fixtures_path: Path, calculator: MetricsCalculator):
        """Test algorithms against edge cases dataset."""
        input_data, expected_output = self.load_test_data(fixtures_path, "edge_cases")
        test_cases = self.convert_to_test_cases(input_data)

        # Calculate metrics
        actual_metrics = calculator.calculate_project_metrics(
            test_cases=test_cases,
            project_key=input_data["project_key"],
            time_window=input_data["time_window"],
        )

        # Assert against gold master
        self.assert_metrics_match(actual_metrics, expected_output)

    @pytest.mark.unit
    def test_large_dataset_algorithms(self, fixtures_path: Path, calculator: MetricsCalculator):
        """Test algorithms against large dataset."""
        input_data, expected_output = self.load_test_data(fixtures_path, "large_dataset")
        test_cases = self.convert_to_test_cases(input_data)

        # Calculate metrics
        actual_metrics = calculator.calculate_project_metrics(
            test_cases=test_cases,
            project_key=input_data["project_key"],
            time_window=input_data["time_window"],
        )

        # Assert against gold master
        self.assert_metrics_match(actual_metrics, expected_output)

    @pytest.mark.unit
    def test_empty_dataset_algorithms(self, calculator: MetricsCalculator):
        """Test algorithms with empty dataset."""
        # Calculate metrics with no test cases
        actual_metrics = calculator.calculate_project_metrics(
            test_cases=[], project_key="EMPTY", time_window="7d"
        )

        # Assert expected behavior for empty dataset
        assert actual_metrics.project_key == "EMPTY"
        assert actual_metrics.time_window == "7d"
        assert actual_metrics.total_tests == 0
        assert actual_metrics.zephyr_tests == 0
        assert actual_metrics.qtest_tests == 0
        assert actual_metrics.adoption_ratio == 0.0
        assert actual_metrics.active_users == 0
        assert actual_metrics.coverage_parity == 0.0
        assert actual_metrics.defect_link_rate == 0.0
        assert len(actual_metrics.team_metrics) == 0

    @pytest.mark.unit
    def test_algorithm_precision(self, fixtures_path: Path, calculator: MetricsCalculator):
        """Test that algorithms maintain precision across repeated calculations."""
        input_data, expected_output = self.load_test_data(fixtures_path, "basic")
        test_cases = self.convert_to_test_cases(input_data)

        # Calculate metrics multiple times
        results = []
        for _ in range(5):
            metrics = calculator.calculate_project_metrics(
                test_cases=test_cases,
                project_key=input_data["project_key"],
                time_window=input_data["time_window"],
            )
            results.append(metrics)

        # All results should be identical
        baseline = results[0]
        for i, result in enumerate(results[1:], 1):
            assert (
                result.adoption_ratio == baseline.adoption_ratio
            ), f"Calculation {i} adoption_ratio differs from baseline"
            assert (
                result.coverage_parity == baseline.coverage_parity
            ), f"Calculation {i} coverage_parity differs from baseline"
            assert (
                result.defect_link_rate == baseline.defect_link_rate
            ), f"Calculation {i} defect_link_rate differs from baseline"

    @pytest.mark.unit
    def test_algorithm_determinism(self, fixtures_path: Path, calculator: MetricsCalculator):
        """Test that algorithms are deterministic regardless of input order."""
        input_data, expected_output = self.load_test_data(fixtures_path, "basic")
        test_cases = self.convert_to_test_cases(input_data)

        # Calculate with original order
        metrics_original = calculator.calculate_project_metrics(
            test_cases=test_cases,
            project_key=input_data["project_key"],
            time_window=input_data["time_window"],
        )

        # Calculate with reversed order
        metrics_reversed = calculator.calculate_project_metrics(
            test_cases=list(reversed(test_cases)),
            project_key=input_data["project_key"],
            time_window=input_data["time_window"],
        )

        # Results should be identical
        assert metrics_original.adoption_ratio == metrics_reversed.adoption_ratio
        assert metrics_original.coverage_parity == metrics_reversed.coverage_parity
        assert metrics_original.defect_link_rate == metrics_reversed.defect_link_rate
        assert metrics_original.active_users == metrics_reversed.active_users

        # Team metrics should also be identical
        assert len(metrics_original.team_metrics) == len(metrics_reversed.team_metrics)
        for team_name in metrics_original.team_metrics:
            orig_team = metrics_original.team_metrics[team_name]
            rev_team = metrics_reversed.team_metrics[team_name]
            assert orig_team.adoption_ratio == rev_team.adoption_ratio

    @pytest.mark.property
    def test_algorithm_properties(self, calculator: MetricsCalculator):
        """Test mathematical properties of algorithms."""

        # Property: adoption_ratio should always be between 0 and 1
        # Create test cases with different ratios
        test_cases_all_zephyr = [
            TestCaseModel(
                id="Z1",
                key="Z1",
                summary="Test",
                project_key="PROP",
                component="Test",
                labels=[],
                assignee="test@example.com",
                source_system="zephyr",
                created=datetime.fromisoformat("2025-06-01T00:00:00+00:00"),
                updated=datetime.fromisoformat("2025-06-01T00:00:00+00:00"),
                status="Done",
                last_execution=datetime.fromisoformat("2025-06-01T00:00:00+00:00"),
                execution_status="PASS",
            )
        ]

        test_cases_all_qtest = [
            TestCaseModel(
                id="Q1",
                key="Q1",
                summary="Test",
                project_key="PROP",
                component="Test",
                labels=[],
                assignee="test@example.com",
                source_system="qtest",
                created=datetime.fromisoformat("2025-06-01T00:00:00+00:00"),
                updated=datetime.fromisoformat("2025-06-01T00:00:00+00:00"),
                status="Done",
                last_execution=datetime.fromisoformat("2025-06-01T00:00:00+00:00"),
                execution_status="PASS",
            )
        ]

        # Test all zephyr (should be 0.0 adoption)
        metrics_all_zephyr = calculator.calculate_project_metrics(
            test_cases=test_cases_all_zephyr, project_key="PROP", time_window="7d"
        )
        assert 0.0 <= metrics_all_zephyr.adoption_ratio <= 1.0
        assert metrics_all_zephyr.adoption_ratio == 0.0  # No qTest adoption

        # Test all qtest (should be undefined, but handled gracefully)
        metrics_all_qtest = calculator.calculate_project_metrics(
            test_cases=test_cases_all_qtest, project_key="PROP", time_window="7d"
        )
        assert 0.0 <= metrics_all_qtest.adoption_ratio <= 1.0

        # Property: total_tests should equal sum of component tests
        metrics = calculator.calculate_project_metrics(
            test_cases=test_cases_all_zephyr + test_cases_all_qtest,
            project_key="PROP",
            time_window="7d",
        )
        component_test_sum = sum(team.total_tests for team in metrics.team_metrics.values())
        assert metrics.total_tests == component_test_sum


class TestGoldMasterValidation:
    """Validate that gold master datasets are internally consistent."""

    @pytest.fixture
    def fixtures_path(self) -> Path:
        """Path to test fixtures directory."""
        return Path(__file__).parent.parent.parent / "testdata" / "fixtures"

    @pytest.mark.unit
    def test_gold_master_consistency(self, fixtures_path: Path):
        """Test that all gold master datasets are internally consistent."""
        datasets = ["basic", "edge_cases", "large_dataset"]

        for dataset_name in datasets:
            input_file = fixtures_path / f"math_input_{dataset_name}.json"
            output_file = fixtures_path / f"math_output_{dataset_name}.json"

            # Both files should exist
            assert input_file.exists(), f"Missing input file: {input_file}"
            assert output_file.exists(), f"Missing output file: {output_file}"

            # Both should be valid JSON
            with open(input_file) as f:
                input_data = json.load(f)

            with open(output_file) as f:
                output_data = json.load(f)

            # Basic consistency checks
            assert input_data["project_key"] == output_data["project_key"]
            assert input_data["time_window"] == output_data["time_window"]

            # Test case count should match total_tests
            test_case_count = len(input_data.get("test_cases", []))
            assert test_case_count == output_data["total_tests"]

            # Source system counts should add up
            zephyr_count = sum(
                1 for tc in input_data.get("test_cases", []) if tc["source_system"] == "zephyr"
            )
            qtest_count = sum(
                1 for tc in input_data.get("test_cases", []) if tc["source_system"] == "qtest"
            )

            assert zephyr_count == output_data["zephyr_tests"]
            assert qtest_count == output_data["qtest_tests"]
            assert zephyr_count + qtest_count == output_data["total_tests"]
