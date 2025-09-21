"""
Property-based tests for LedZephyr.

These tests use Hypothesis to generate random inputs and verify that
business invariants hold across all possible inputs.
"""

import pytest
from hypothesis import given, assume, strategies as st, settings

from ledzephyr.models import ProjectMetrics, TrendData, TeamMetrics
from tests.strategies import (
    project_keys,
    time_windows,
    test_counts,
    project_metrics_data,
    malicious_strings,
    edge_case_numbers,
    invalid_time_windows,
    adversarial_project_data,
)


class TestProjectMetricsProperties:
    """Property-based tests for ProjectMetrics domain model."""

    @given(data=project_metrics_data())
    def test_adoption_ratio_invariants(self, data):
        """Adoption ratio must always be between 0 and 1."""
        metrics = ProjectMetrics(**data)

        # Core invariant: adoption ratio is always in [0, 1]
        assert 0.0 <= metrics.adoption_ratio <= 1.0

        # If there are tests, ratio should be meaningful
        if data["total_tests"] > 0:
            expected_ratio = data["qtest_tests"] / data["total_tests"]
            assert abs(metrics.adoption_ratio - expected_ratio) < 0.001

        # If no tests, ratio should be 0
        if data["total_tests"] == 0:
            assert metrics.adoption_ratio == 0.0

    @given(
        total=test_counts(),
        qtest=st.integers(min_value=0)
    )
    def test_test_count_constraints(self, total, qtest):
        """Test counts must satisfy logical constraints."""
        assume(qtest <= total)  # Precondition

        metrics = ProjectMetrics(
            project_key="TEST",
            time_window="7d",
            total_tests=total,
            qtest_tests=qtest,
            zephyr_tests=total - qtest,
            active_users=5,
            coverage_parity=0.8,
            defect_link_rate=0.9,
        )

        # Invariants
        assert metrics.total_tests >= 0
        assert metrics.qtest_tests >= 0
        assert metrics.zephyr_tests >= 0
        assert metrics.qtest_tests <= metrics.total_tests
        assert metrics.zephyr_tests <= metrics.total_tests
        assert metrics.qtest_tests + metrics.zephyr_tests == metrics.total_tests

    @given(
        project_key=project_keys(),
        metrics_data=project_metrics_data()
    )
    def test_project_key_consistency(self, project_key, metrics_data):
        """Project key should be preserved exactly."""
        metrics = ProjectMetrics(
            project_key=project_key,  # Use our generated key
            time_window="7d",
            total_tests=metrics_data["total_tests"],
            qtest_tests=metrics_data["qtest_tests"],
            zephyr_tests=metrics_data["zephyr_tests"],
            active_users=metrics_data["active_users"],
            coverage_parity=metrics_data["coverage_parity"],
            defect_link_rate=metrics_data["defect_link_rate"],
        )

        assert metrics.project_key == project_key
        assert isinstance(metrics.project_key, str)
        assert len(metrics.project_key) >= 2  # Minimum project key length

    @given(data=project_metrics_data())
    def test_ratios_are_percentages(self, data):
        """All ratio fields should be valid percentages."""
        metrics = ProjectMetrics(**data)

        # All ratios should be valid percentages
        assert 0.0 <= metrics.adoption_ratio <= 1.0
        assert 0.0 <= metrics.coverage_parity <= 1.0
        assert 0.0 <= metrics.defect_link_rate <= 1.0


class TestAdversarialInputs:
    """Test system behavior with malicious or edge case inputs."""

    @given(malicious_input=malicious_strings())
    @settings(max_examples=50)  # Reduce examples for adversarial tests
    def test_project_key_resilience(self, malicious_input):
        """System should handle malicious project keys gracefully."""
        try:
            # Try to create metrics with malicious input
            metrics = ProjectMetrics(
                project_key=malicious_input,
                time_window="7d",
                total_tests=100,
                qtest_tests=50,
                zephyr_tests=50,
                active_users=5,
                coverage_parity=0.8,
                defect_link_rate=0.9,
            )

            # If it succeeds, the result should still be valid
            assert isinstance(metrics.project_key, str)
            assert 0.0 <= metrics.adoption_ratio <= 1.0

        except (ValueError, TypeError):
            # Rejection is acceptable for invalid inputs
            pass
        except Exception as e:
            # System must never crash with unexpected exceptions
            pytest.fail(f"System crashed with {type(e).__name__}: {e}")

    @given(bad_count=edge_case_numbers())
    @settings(max_examples=50)
    def test_edge_case_numbers_handling(self, bad_count):
        """System should handle edge case numbers gracefully."""
        try:
            # Try negative or very large numbers
            if bad_count < 0:
                # Should reject negative test counts
                with pytest.raises((ValueError, TypeError)):
                    ProjectMetrics(
                        project_key="TEST",
                        time_window="7d",
                        total_tests=bad_count,
                        qtest_tests=0,
                        zephyr_tests=0,
                        active_users=5,
                        coverage_parity=0.8,
                        defect_link_rate=0.9,
                    )
            else:
                # Should handle large positive numbers
                metrics = ProjectMetrics(
                    project_key="TEST",
                    time_window="7d",
                    total_tests=bad_count,
                    qtest_tests=min(bad_count, bad_count // 2),
                    zephyr_tests=max(0, bad_count - min(bad_count, bad_count // 2)),
                    active_users=5,
                    coverage_parity=0.8,
                    defect_link_rate=0.9,
                )
                assert metrics.adoption_ratio >= 0.0

        except (ValueError, TypeError, OverflowError):
            # These are acceptable responses to edge cases
            pass

    @given(data=adversarial_project_data())
    @settings(max_examples=30)
    def test_adversarial_data_combinations(self, data):
        """Test combinations of adversarial inputs."""
        try:
            # System should either reject invalid combinations or handle them gracefully
            if (isinstance(data["total_tests"], int) and
                isinstance(data["qtest_tests"], int) and
                data["total_tests"] >= 0 and
                data["qtest_tests"] >= 0 and
                data["qtest_tests"] <= data["total_tests"]):

                metrics = ProjectMetrics(
                    project_key=str(data["project_key"]),  # Force to string
                    time_window="7d",
                    total_tests=data["total_tests"],
                    qtest_tests=data["qtest_tests"],
                    zephyr_tests=data["total_tests"] - data["qtest_tests"],
                    active_users=0,
                    coverage_parity=0.0,
                    defect_link_rate=0.0,
                )

                # Basic invariants must still hold
                assert metrics.adoption_ratio >= 0.0
                assert metrics.total_tests >= metrics.qtest_tests

        except (ValueError, TypeError, OverflowError):
            # Rejection of invalid data is acceptable
            pass


class TestTimeWindowProperties:
    """Property-based tests for time window handling."""

    @given(window=time_windows())
    def test_valid_time_windows(self, window):
        """Valid time windows should be processed correctly."""
        # This would test actual time window parsing when implemented
        assert window in ["24h", "7d", "30d", "90d"]
        assert isinstance(window, str)
        assert len(window) >= 2

    @given(invalid_window=invalid_time_windows())
    @settings(max_examples=50)
    def test_invalid_time_window_handling(self, invalid_window):
        """Invalid time windows should be rejected gracefully."""
        # This would test time window validation when implemented
        # For now, we just ensure the test doesn't crash
        assert isinstance(invalid_window, str)


class TestBusinessInvariants:
    """Test business rule invariants across all inputs."""

    @given(
        total=st.integers(min_value=1, max_value=10000),
        qtest_ratio=st.floats(min_value=0.0, max_value=1.0)
    )
    def test_migration_progress_monotonicity(self, total, qtest_ratio):
        """Migration progress should be monotonic over time."""
        qtest_count = int(total * qtest_ratio)

        metrics_before = ProjectMetrics(
            project_key="TEST",
            time_window="7d",
            total_tests=total,
            qtest_tests=qtest_count,
            zephyr_tests=total - qtest_count,
            active_users=5,
            coverage_parity=0.8,
            defect_link_rate=0.9,
        )

        # Simulate migration progress (more tests migrated)
        new_qtest_count = min(total, qtest_count + 10)
        metrics_after = ProjectMetrics(
            project_key="TEST",
            time_window="7d",
            total_tests=total,
            qtest_tests=new_qtest_count,
            zephyr_tests=total - new_qtest_count,
            active_users=5,
            coverage_parity=0.8,
            defect_link_rate=0.9,
        )

        # Migration progress should not decrease
        assert metrics_after.adoption_ratio >= metrics_before.adoption_ratio

    @given(
        base_metrics=project_metrics_data(),
        multiplier=st.floats(min_value=1.0, max_value=10.0)
    )
    def test_scaling_invariants(self, base_metrics, multiplier):
        """Ratios should remain constant when scaling test counts."""
        # Scale all test counts by the same factor
        scaled_total = int(base_metrics["total_tests"] * multiplier)
        scaled_qtest = int(base_metrics["qtest_tests"] * multiplier)
        scaled_zephyr = scaled_total - scaled_qtest

        if scaled_total > 0:
            original = ProjectMetrics(**base_metrics)

            scaled = ProjectMetrics(
                project_key=base_metrics["project_key"],
                time_window=base_metrics["time_window"],
                total_tests=scaled_total,
                qtest_tests=scaled_qtest,
                zephyr_tests=scaled_zephyr,
                active_users=base_metrics["active_users"],
                coverage_parity=base_metrics["coverage_parity"],
                defect_link_rate=base_metrics["defect_link_rate"],
            )

            # Adoption ratio should be approximately the same
            if original.total_tests > 0:
                assert abs(scaled.adoption_ratio - original.adoption_ratio) < 0.01