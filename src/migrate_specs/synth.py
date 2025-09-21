"""MECE pairwise test data generation."""

from __future__ import annotations

import random
from collections.abc import Sequence

import pandas as pd
from allpairspy import AllPairs


def pairwise_df(factors: dict[str, Sequence], seed: int = 42) -> pd.DataFrame:
    """
    Generate pairwise combinatorial test data using AllPairs algorithm.

    Args:
        factors: Dictionary mapping factor names to their possible values
        seed: Random seed for deterministic generation

    Returns:
        DataFrame with pairwise test combinations
    """
    random.seed(seed)

    if not factors:
        return pd.DataFrame()

    keys = list(factors.keys())
    values = [list(v) for v in factors.values()]

    # Handle single factor case (AllPairs requires at least 2 factors)
    if len(values) < 2:
        data = [{keys[0]: val} for val in values[0]]
        return pd.DataFrame.from_records(data)

    # Generate all pairwise combinations
    rows = list(AllPairs(values))

    # Convert to list of dictionaries
    data = [dict(zip(keys, row, strict=False)) for row in rows]

    return pd.DataFrame.from_records(data)
