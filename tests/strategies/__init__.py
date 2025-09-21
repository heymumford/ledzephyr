"""
Hypothesis strategies for property-based testing.

This module contains reusable strategies for generating test data
that conforms to domain constraints and business rules.
"""

from .project_strategies import (
    project_keys,
    time_windows,
    test_counts,
    project_metrics_data,
    team_names,
    team_metrics_data,
)

from .config_strategies import (
    valid_urls,
    api_tokens,
    config_data,
)

from .adversarial_strategies import (
    malicious_strings,
    edge_case_numbers,
    invalid_time_windows,
    adversarial_project_data,
)

__all__ = [
    # Project strategies
    "project_keys",
    "time_windows",
    "test_counts",
    "project_metrics_data",
    "team_names",
    "team_metrics_data",
    # Config strategies
    "valid_urls",
    "api_tokens",
    "config_data",
    # Adversarial strategies
    "malicious_strings",
    "edge_case_numbers",
    "invalid_time_windows",
    "adversarial_project_data",
]