"""Gold master dataset assembly with simulated API activity."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

from .synth import pairwise_df


def build_gold_master(out_dir: Path, days: int = 30, seed: int = 42) -> pd.DataFrame:
    """
    Build gold master dataset with simulated API activity and categorical factors.

    Args:
        out_dir: Output directory for generated files
        days: Number of days to simulate
        seed: Random seed for reproducible generation

    Returns:
        DataFrame with gold master test data
    """
    rng = np.random.default_rng(seed)
    Faker.seed(seed)

    # Generate date range ending at current time
    dates = pd.date_range(end=pd.Timestamp.utcnow().normalize(), periods=days, freq="D")

    # Pairwise factors illustrative for cross-tool joins
    factors = {
        "jira_issue_status": ["Open", "InProgress", "Done"],
        "priority": ["P1", "P2"],
        "has_attachment": [True, False],
    }
    grid = pairwise_df(factors, seed=seed)

    # Expand across days with controlled seasonality and noise
    base = []
    for d in dates:
        for _, row in grid.iterrows():
            # Zephyr activity with weekly seasonality (peak mid-week)
            day_of_week = d.dayofweek  # 0=Monday, 6=Sunday
            weekly_factor = 1.5 if 1 <= day_of_week <= 4 else 0.8  # Higher mid-week
            zephyr_base = 5 * weekly_factor
            z = max(0, int(rng.poisson(zephyr_base) + 2 * np.sin(2 * np.pi * d.dayofyear / 7)))

            # qTest activity with different pattern (inverse weekly)
            qtest_base = 8 * (2.0 - weekly_factor)  # Higher on weekends
            q = max(0, int(rng.poisson(qtest_base) + 2 * np.cos(2 * np.pi * d.dayofyear / 7)))

            base.append(
                {"date": d.date(), "zephyr_activity": z, "qtest_activity": q, **row.to_dict()}
            )

    df = pd.DataFrame(base)

    # Ensure output directory exists
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save in both formats
    df.to_parquet(out_dir / "gold_master.parquet", index=False)
    df.to_csv(out_dir / "gold_master.csv", index=False)

    return df
