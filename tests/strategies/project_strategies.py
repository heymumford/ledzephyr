"""
Hypothesis strategies for project-related data.
"""

from hypothesis import strategies as st
from typing import Dict, Any


@st.composite
def project_keys(draw) -> str:
    """Generate valid project keys following Jira conventions."""
    # Jira project keys are 2-10 uppercase letters
    return draw(st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        min_size=2,
        max_size=10
    ))


@st.composite
def time_windows(draw) -> str:
    """Generate valid time window strings."""
    valid_windows = ["24h", "7d", "30d", "90d"]
    return draw(st.sampled_from(valid_windows))


@st.composite
def test_counts(draw) -> int:
    """Generate realistic test counts."""
    # Most projects have 0-10,000 tests, with some edge cases
    return draw(st.one_of(
        st.integers(min_value=0, max_value=50),      # Small projects
        st.integers(min_value=51, max_value=500),    # Medium projects
        st.integers(min_value=501, max_value=10000), # Large projects
        st.just(0),                                  # Empty projects
        st.integers(min_value=10001, max_value=50000) # Very large (rare)
    ))


@st.composite
def project_metrics_data(draw) -> Dict[str, Any]:
    """Generate complete project metrics data."""
    project_key = draw(project_keys())
    time_window = draw(time_windows())
    total_tests = draw(test_counts())

    # qTest tests cannot exceed total tests
    qtest_tests = draw(st.integers(min_value=0, max_value=total_tests))

    # Zephyr tests are remaining tests
    zephyr_tests = total_tests - qtest_tests

    # Active users should be reasonable
    active_users = draw(st.integers(min_value=0, max_value=100))

    # Coverage parity is a ratio
    coverage_parity = draw(st.floats(min_value=0.0, max_value=1.0))

    # Defect link rate is a ratio
    defect_link_rate = draw(st.floats(min_value=0.0, max_value=1.0))

    # Calculate adoption ratio
    adoption_ratio = qtest_tests / total_tests if total_tests > 0 else 0.0

    return {
        "project_key": project_key,
        "time_window": time_window,
        "total_tests": total_tests,
        "qtest_tests": qtest_tests,
        "zephyr_tests": zephyr_tests,
        "adoption_ratio": adoption_ratio,
        "active_users": active_users,
        "coverage_parity": coverage_parity,
        "defect_link_rate": defect_link_rate,
    }


@st.composite
def team_names(draw) -> str:
    """Generate realistic team names."""
    team_prefixes = ["Team", "Squad", "Tribe", "Group", "Unit"]
    team_suffixes = ["Alpha", "Beta", "Core", "Platform", "API", "Web", "Mobile", "Data"]

    prefix = draw(st.sampled_from(team_prefixes))
    suffix = draw(st.sampled_from(team_suffixes))

    return f"{prefix} {suffix}"


@st.composite
def team_metrics_data(draw) -> Dict[str, Any]:
    """Generate team metrics data."""
    team_name = draw(team_names())
    projects = draw(st.lists(project_keys(), min_size=1, max_size=10, unique=True))

    # Generate metrics for each project
    team_data = {}
    for project in projects:
        metrics = draw(project_metrics_data())
        metrics["project_key"] = project  # Override with our project key
        team_data[project] = metrics

    return {
        "team_name": team_name,
        "projects": team_data,
    }


@st.composite
def trend_data(draw) -> Dict[str, Dict[str, float]]:
    """Generate 4-week trend data."""
    weeks = ["week_1", "week_2", "week_3", "week_4"]
    trend = {}

    # Generate correlated data (trends should be somewhat consistent)
    base_adoption = draw(st.floats(min_value=0.0, max_value=1.0))
    base_coverage = draw(st.floats(min_value=0.0, max_value=1.0))
    base_users = draw(st.integers(min_value=0, max_value=50))

    for week in weeks:
        # Add some variation but keep it realistic
        adoption_var = draw(st.floats(min_value=-0.1, max_value=0.1))
        coverage_var = draw(st.floats(min_value=-0.1, max_value=0.1))
        users_var = draw(st.integers(min_value=-5, max_value=5))

        trend[week] = {
            "adoption_ratio": max(0.0, min(1.0, base_adoption + adoption_var)),
            "coverage_parity": max(0.0, min(1.0, base_coverage + coverage_var)),
            "active_users": max(0, base_users + users_var),
        }

    return trend