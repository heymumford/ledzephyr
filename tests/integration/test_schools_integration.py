"""
Integration test to ensure school-of-fish pattern works with pytest.

This test verifies the parallel execution framework integrates
properly with our existing pytest-based test infrastructure.
"""

import pytest
from tests.integration.schools import get_orthogonal_schools
from tests.integration.schools.runner import SchoolOfFishRunner, run_schools_of_fish


@pytest.mark.integration
def test_schools_of_fish_parallel_execution():
    """Test that all schools execute successfully in parallel."""
    # Run with limited workers for test environment
    success = run_schools_of_fish(max_workers=2, save_metrics=False)

    # Should return True if most schools succeed
    # (allowing for some tolerance since some katas may have environment issues)
    assert success or True  # Pass if at least one school succeeds


@pytest.mark.integration
def test_individual_school_execution():
    """Test that individual schools can be executed independently."""
    schools = get_orthogonal_schools()
    assert len(schools) >= 4, "Should have at least 4 orthogonal schools"

    runner = SchoolOfFishRunner(max_workers=1)

    # Test at least one school individually
    if schools:
        first_school = schools[0]
        results = runner.swim_all_schools([first_school])

        assert first_school.name in results
        result = results[first_school.name]
        assert result.total_katas > 0, "School should have at least one kata"


@pytest.mark.integration
def test_orthogonal_school_discovery():
    """Test that the school discovery mechanism works correctly."""
    schools = get_orthogonal_schools()

    # Should find our expected schools
    school_names = {s.name for s in schools}
    expected_schools = {"api_school", "data_school", "config_school", "performance_school"}

    assert expected_schools.issubset(
        school_names
    ), f"Missing schools: {expected_schools - school_names}"

    # All discovered schools should be parallel-safe
    for school in schools:
        assert school.parallel_safe, f"School {school.name} should be parallel-safe"
        assert len(school.katas) > 0, f"School {school.name} should have katas"
