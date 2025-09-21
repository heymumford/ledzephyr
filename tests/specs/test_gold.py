"""Test gold master dataset assembly."""

import pandas as pd
import pytest

from migrate_specs import gold


@pytest.mark.unit
def test_gold_master_parquet(tmp_path):
    """Test building gold master dataset with parquet output."""
    # Arrange
    out = tmp_path / "gold"
    out.mkdir()

    # Act
    df = gold.build_gold_master(out)

    # Assert - schema columns we rely on downstream
    required_columns = ["date", "zephyr_activity", "qtest_activity", "jira_issue_status"]
    for col in required_columns:
        assert col in df.columns, f"Missing required column: {col}"

    # Verify output files were created
    assert (out / "gold_master.parquet").exists()
    assert (out / "gold_master.csv").exists()

    # Verify data types and ranges
    assert df["zephyr_activity"].dtype in ["int32", "int64"]
    assert df["qtest_activity"].dtype in ["int32", "int64"]
    assert all(df["zephyr_activity"] >= 0)
    assert all(df["qtest_activity"] >= 0)

    # Verify we have data for multiple days
    assert len(df["date"].unique()) > 1


@pytest.mark.unit
def test_gold_master_deterministic(tmp_path):
    """Test that gold master generation is deterministic."""
    # Arrange
    out1 = tmp_path / "gold1"
    out2 = tmp_path / "gold2"
    out1.mkdir()
    out2.mkdir()

    # Act - generate twice with same seed
    df1 = gold.build_gold_master(out1, days=10, seed=42)
    df2 = gold.build_gold_master(out2, days=10, seed=42)

    # Assert - should be identical
    pd.testing.assert_frame_equal(df1, df2)


@pytest.mark.unit
def test_gold_master_custom_parameters(tmp_path):
    """Test gold master with custom parameters."""
    # Arrange
    out = tmp_path / "gold"
    out.mkdir()
    custom_days = 5

    # Act
    df = gold.build_gold_master(out, days=custom_days, seed=123)

    # Assert
    assert len(df["date"].unique()) == custom_days

    # Should have some variety in the pairwise factors
    status_values = df["jira_issue_status"].unique()
    assert len(status_values) > 1  # Should have multiple statuses


@pytest.mark.unit
def test_gold_master_file_formats(tmp_path):
    """Test that both parquet and CSV files are created correctly."""
    # Arrange
    out = tmp_path / "gold"
    out.mkdir()

    # Act
    df = gold.build_gold_master(out, days=7, seed=42)

    # Assert - verify files exist and are readable
    parquet_file = out / "gold_master.parquet"
    csv_file = out / "gold_master.csv"

    assert parquet_file.exists()
    assert csv_file.exists()

    # Verify we can read both formats and they match
    df_parquet = pd.read_parquet(parquet_file)
    df_csv = pd.read_csv(csv_file)

    # Convert date column for comparison (CSV reads as string)
    df_csv["date"] = pd.to_datetime(df_csv["date"]).dt.date

    pd.testing.assert_frame_equal(df_parquet, df_csv)


@pytest.mark.unit
def test_gold_master_seasonality_simulation(tmp_path):
    """Test that data includes seasonal patterns."""
    # Arrange
    out = tmp_path / "gold"
    out.mkdir()

    # Act - generate longer series to see patterns
    df = gold.build_gold_master(out, days=28, seed=42)

    # Assert - check for variance in activity levels
    zephyr_variance = df["zephyr_activity"].var()
    qtest_variance = df["qtest_activity"].var()

    # Should have some variance (not all the same values)
    assert zephyr_variance > 0
    assert qtest_variance > 0

    # Activity levels should be reasonable (not all zero, not extremely high)
    assert df["zephyr_activity"].max() < 50  # Reasonable upper bound
    assert df["qtest_activity"].max() < 50  # Reasonable upper bound
