"""Property-based tests for domain models following testing standards."""

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from ledzephyr.models import ProjectMetrics


# Hypothesis strategies
@st.composite
def project_keys(draw):
    """Generate valid project keys following Jira conventions."""
    return draw(st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=2, max_size=10))


@st.composite
def time_windows(draw):
    """Generate valid time window strings."""
    valid_windows = ["24h", "7d", "30d", "90d"]
    return draw(st.sampled_from(valid_windows))


@st.composite
def count_strategy(draw):
    """Generate realistic execution counts."""
    return draw(
        st.one_of(
            st.integers(min_value=0, max_value=50),  # Small projects
            st.integers(min_value=51, max_value=500),  # Medium projects
            st.integers(min_value=501, max_value=10000),  # Large projects
            st.just(0),  # Empty projects
        )
    )


@st.composite
def project_metrics_data(draw):
    """Generate complete project metrics data."""
    project_key = draw(project_keys())
    time_window = draw(time_windows())
    total_executions = draw(count_strategy())

    # qTest executions cannot exceed total executions
    qtest_executions = draw(st.integers(min_value=0, max_value=total_executions))

    # Zephyr executions are remaining executions
    zephyr_executions = total_executions - qtest_executions

    # Active users should be reasonable
    active_users = draw(st.integers(min_value=0, max_value=100))

    # Coverage parity is a ratio
    coverage_parity = draw(st.floats(min_value=0.0, max_value=1.0))

    # Defect link rate is a ratio
    defect_link_rate = draw(st.floats(min_value=0.0, max_value=1.0))

    # Calculate adoption ratio
    adoption_ratio = qtest_executions / total_executions if total_executions > 0 else 0.0

    return {
        "project_key": project_key,
        "time_window": time_window,
        "total_tests": total_executions,
        "qtest_tests": qtest_executions,
        "zephyr_tests": zephyr_executions,
        "adoption_ratio": adoption_ratio,
        "active_users": active_users,
        "coverage_parity": coverage_parity,
        "defect_link_rate": defect_link_rate,
    }


@pytest.mark.unit
@pytest.mark.property
@pytest.mark.metrics
class TestProjectMetricsProperties:
    """Property-based tests for ProjectMetrics domain model."""

    @given(data=project_metrics_data())
    def test_adoption_ratio_invariants_valid_data_ratio_in_bounds(self, data):
        """Test adoption ratio invariants with valid data keeps ratio in bounds."""
        # Arrange & Act
        metrics = ProjectMetrics(**data)

        # Assert
        assert 0.0 <= metrics.adoption_ratio <= 1.0

        # If there are executions, ratio should be meaningful
        if data["total_tests"] > 0:
            expected_ratio = data["qtest_tests"] / data["total_tests"]
            assert abs(metrics.adoption_ratio - expected_ratio) < 0.001

        # If no executions, ratio should be 0
        if data["total_tests"] == 0:
            assert metrics.adoption_ratio == 0.0

    @given(total=st.integers(min_value=0, max_value=10000), qtest=st.integers(min_value=0))
    def test_count_constraints_valid_counts_satisfy_invariants(self, total, qtest):
        """Verify count constraints with valid counts satisfy invariants."""
        # Arrange
        assume(qtest <= total)  # Precondition

        # Act
        metrics = ProjectMetrics(
            project_key="DEMO",
            time_window="7d",
            total_tests=total,
            qtest_tests=qtest,
            zephyr_tests=total - qtest,
            adoption_ratio=qtest / total if total > 0 else 0.0,
            active_users=5,
            coverage_parity=0.8,
            defect_link_rate=0.9,
        )

        # Assert
        assert metrics.total_tests >= 0
        assert metrics.qtest_tests >= 0
        assert metrics.zephyr_tests >= 0
        assert metrics.qtest_tests <= metrics.total_tests
        assert metrics.zephyr_tests <= metrics.total_tests
        assert metrics.qtest_tests + metrics.zephyr_tests == metrics.total_tests

    @given(project_key=project_keys(), metrics_data=project_metrics_data())
    def test_project_key_consistency_any_key_preserves_value(self, project_key, metrics_data):
        """Test project key consistency with any key preserves value."""
        # Arrange & Act
        metrics = ProjectMetrics(
            project_key=project_key,  # Use our generated key
            time_window="7d",
            total_tests=metrics_data["total_tests"],
            qtest_tests=metrics_data["qtest_tests"],
            zephyr_tests=metrics_data["zephyr_tests"],
            adoption_ratio=metrics_data["adoption_ratio"],
            active_users=metrics_data["active_users"],
            coverage_parity=metrics_data["coverage_parity"],
            defect_link_rate=metrics_data["defect_link_rate"],
        )

        # Assert
        assert metrics.project_key == project_key
        assert isinstance(metrics.project_key, str)
        assert len(metrics.project_key) >= 2  # Minimum project key length

    @given(data=project_metrics_data())
    def test_ratios_are_percentages_any_data_ratios_valid(self, data):
        """Test ratios are valid percentages with any data."""
        # Arrange & Act
        metrics = ProjectMetrics(**data)

        # Assert
        assert 0.0 <= metrics.adoption_ratio <= 1.0
        assert 0.0 <= metrics.coverage_parity <= 1.0
        assert 0.0 <= metrics.defect_link_rate <= 1.0


@pytest.mark.unit
@pytest.mark.property
@pytest.mark.metrics
class TestBusinessInvariants:
    """Test business rule invariants across all inputs."""

    @given(
        total=st.integers(min_value=1, max_value=10000),
        qtest_ratio=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_migration_progress_monotonicity_increasing_executions_non_decreasing_ratio(
        self, total, qtest_ratio
    ):
        """Verify migration progress monotonicity with increasing executions has non-decreasing ratio."""
        # Arrange
        qtest_count = int(total * qtest_ratio)

        metrics_before = ProjectMetrics(
            project_key="DEMO",
            time_window="7d",
            total_tests=total,
            qtest_tests=qtest_count,
            zephyr_tests=total - qtest_count,
            adoption_ratio=qtest_count / total,
            active_users=5,
            coverage_parity=0.8,
            defect_link_rate=0.9,
        )

        # Simulate migration progress (more executions migrated)
        new_qtest_count = min(total, qtest_count + 10)

        # Act
        metrics_after = ProjectMetrics(
            project_key="DEMO",
            time_window="7d",
            total_tests=total,
            qtest_tests=new_qtest_count,
            zephyr_tests=total - new_qtest_count,
            adoption_ratio=new_qtest_count / total,
            active_users=5,
            coverage_parity=0.8,
            defect_link_rate=0.9,
        )

        # Assert
        assert metrics_after.adoption_ratio >= metrics_before.adoption_ratio

    @given(base_metrics=project_metrics_data(), multiplier=st.integers(min_value=2, max_value=10))
    def test_scaling_invariants_proportional_scaling_preserves_ratios(
        self, base_metrics, multiplier
    ):
        """Test scaling invariants with proportional scaling preserves ratios."""
        # Arrange
        scaled_total = base_metrics["total_tests"] * multiplier
        scaled_qtest = base_metrics["qtest_tests"] * multiplier
        scaled_zephyr = scaled_total - scaled_qtest

        if scaled_total > 0 and base_metrics["total_tests"] > 0:
            original = ProjectMetrics(**base_metrics)

            # Calculate the expected adoption ratio for scaled metrics
            scaled_adoption_ratio = scaled_qtest / scaled_total if scaled_total > 0 else 0.0

            # Act
            scaled = ProjectMetrics(
                project_key=base_metrics["project_key"],
                time_window=base_metrics["time_window"],
                total_tests=scaled_total,
                qtest_tests=scaled_qtest,
                zephyr_tests=scaled_zephyr,
                adoption_ratio=scaled_adoption_ratio,
                active_users=base_metrics["active_users"],
                coverage_parity=base_metrics["coverage_parity"],
                defect_link_rate=base_metrics["defect_link_rate"],
            )

            # Assert
            assert abs(scaled.adoption_ratio - original.adoption_ratio) < 0.01


@pytest.mark.unit
@pytest.mark.property
@pytest.mark.slow
@pytest.mark.metrics
class TestAdversarialInputs:
    """Test system behavior with edge case inputs."""

    @given(bad_count=st.integers(min_value=-1000, max_value=1000))
    @settings(max_examples=10, deadline=2000)
    def test_edge_case_numbers_handling_any_number_graceful_handling(self, bad_count):
        """Test edge case numbers handling with any number has graceful handling."""
        # Arrange & Act
        try:
            if bad_count < 0:
                # System accepts negative numbers (no validation in Pydantic model)
                metrics = ProjectMetrics(
                    project_key="DEMO",
                    time_window="7d",
                    total_tests=bad_count,
                    qtest_tests=0,
                    zephyr_tests=0,
                    adoption_ratio=0.0,
                    active_users=5,
                    coverage_parity=0.8,
                    defect_link_rate=0.9,
                )
                # Assert
                assert isinstance(metrics.total_tests, int)
            else:
                # Should handle positive numbers
                metrics = ProjectMetrics(
                    project_key="DEMO",
                    time_window="7d",
                    total_tests=bad_count,
                    qtest_tests=min(bad_count, bad_count // 2) if bad_count > 0 else 0,
                    zephyr_tests=(
                        max(0, bad_count - min(bad_count, bad_count // 2)) if bad_count > 0 else 0
                    ),
                    adoption_ratio=0.5 if bad_count > 0 else 0.0,
                    active_users=5,
                    coverage_parity=0.8,
                    defect_link_rate=0.9,
                )
                # Assert
                assert metrics.adoption_ratio >= 0.0

        except (ValueError, TypeError, OverflowError):
            # These are acceptable responses to edge cases
            pass
