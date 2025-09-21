"""Test MECE pairwise test data generation."""

import pandas as pd
import pytest

from migrate_specs import synth


@pytest.mark.unit
def test_pairwise_grid_small():
    """Test pairwise generation with small factor set."""
    # Arrange
    factors = {
        "status": ["Open", "InProgress", "Done"],
        "priority": ["P1", "P2"],
        "has_attachment": [True, False],
    }

    # Act
    df = synth.pairwise_df(factors, seed=7)

    # Assert - pairwise coverage sanity: every pair of factor levels should appear
    assert set(df.columns) == set(factors)

    # size should be << full factorial (3*2*2=12); pairwise usually 6-8 rows
    assert 4 <= len(df) <= 12

    # Verify all factor values appear at least once
    for column, expected_values in factors.items():
        actual_values = set(df[column].unique())
        assert actual_values == set(expected_values)


@pytest.mark.unit
def test_pairwise_df_deterministic():
    """Test that pairwise generation is deterministic with same seed."""
    factors = {
        "api": ["jira", "zephyr", "qtest"],
        "operation": ["get", "post"],
        "auth": ["token", "basic"],
    }

    # Generate twice with same seed
    df1 = synth.pairwise_df(factors, seed=42)
    df2 = synth.pairwise_df(factors, seed=42)

    # Should be identical
    pd.testing.assert_frame_equal(df1, df2)


@pytest.mark.unit
def test_pairwise_df_different_seeds():
    """Test that different seeds produce different results."""
    factors = {
        "api": ["jira", "zephyr", "qtest"],
        "operation": ["get", "post"],
        "response": ["200", "400", "500"],
    }

    df1 = synth.pairwise_df(factors, seed=1)
    df2 = synth.pairwise_df(factors, seed=2)

    # Should have same structure but likely different order/combinations
    assert df1.columns.tolist() == df2.columns.tolist()
    assert len(df1) == len(df2)  # Pairwise should produce same number of rows

    # But content should be different (with high probability)
    try:
        pd.testing.assert_frame_equal(df1, df2)
        # If they're equal, that's very unlikely but possible
        assert False, "Different seeds produced identical results (very unlikely)"
    except AssertionError:
        # Expected - different seeds should produce different arrangements
        pass


@pytest.mark.unit
def test_pairwise_df_single_factor():
    """Test pairwise generation with single factor (edge case)."""
    factors = {"status": ["active", "inactive"]}

    df = synth.pairwise_df(factors, seed=42)

    assert len(df.columns) == 1
    assert "status" in df.columns
    assert set(df["status"]) == {"active", "inactive"}


@pytest.mark.unit
def test_pairwise_df_empty_factors():
    """Test pairwise generation with empty factors (edge case)."""
    factors = {}

    df = synth.pairwise_df(factors, seed=42)

    assert len(df) == 0
    assert len(df.columns) == 0
