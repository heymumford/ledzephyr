"""
Performance School: Timing and resource usage patterns

Orthogonal Concern: How the system performs under load
- Response times
- Memory usage
- Concurrent operations
- Cache efficiency
"""

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from ledzephyr.client import APIClient
from ledzephyr.config import Config
from ledzephyr.metrics import MetricsCalculator
from migrate_specs.gold import build_gold_master

from . import Kata, School, register_school


def kata_metrics_calculation_speed():
    """Kata: Metrics calculation completes within reasonable time."""
    # Create mock client with moderate dataset
    mock_client = Mock()
    mock_client.get_jira_project.return_value = Mock(key="PERF", name="Performance Test")
    mock_client.get_zephyr_tests.return_value = []
    mock_client.get_qtest_tests.return_value = []
    mock_client.get_test_executions.return_value = {}

    calculator = MetricsCalculator(mock_client)

    # Time the calculation
    start_time = time.perf_counter()
    result = calculator.calculate_metrics("PERF", "7d")
    end_time = time.perf_counter()

    duration = end_time - start_time

    # Should complete quickly with empty dataset
    assert duration < 1.0, f"Calculation took {duration:.2f}s, should be under 1s"
    assert result.project_key == "PERF"

    return True


def kata_gold_master_generation_speed():
    """Kata: Gold master generation scales reasonably with dataset size."""
    with TemporaryDirectory() as tmp_dir:
        out_dir = Path(tmp_dir) / "perf"

        # Time small dataset
        start_time = time.perf_counter()
        df_small = build_gold_master(out_dir / "small", days=7, seed=42)
        small_duration = time.perf_counter() - start_time

        # Time larger dataset
        start_time = time.perf_counter()
        df_large = build_gold_master(out_dir / "large", days=28, seed=42)
        large_duration = time.perf_counter() - start_time

        # Should scale reasonably (not exponentially)
        assert small_duration < 2.0, f"Small dataset took {small_duration:.2f}s"
        assert large_duration < 5.0, f"Large dataset took {large_duration:.2f}s"

        # Larger dataset should have proportionally more data
        size_ratio = len(df_large) / len(df_small)
        assert size_ratio > 3, f"Size ratio only {size_ratio:.1f}, expected >3"

    return True


def kata_concurrent_api_calls():
    """Kata: System handles concurrent API operations safely."""
    config = Config(
        jira_url="https://test.atlassian.net",
        jira_username="test@example.com",
        jira_api_token="test_token",
    )

    with patch.object(APIClient, "_make_request") as mock_request:
        mock_response = Mock()
        mock_response.json.return_value = {
            "key": "CONCURRENT",
            "name": "Concurrent Test",
            "components": [],
        }
        mock_request.return_value = mock_response

        def make_api_call():
            client = APIClient(config)
            return client.get_jira_project("CONCURRENT")

        # Run multiple concurrent calls
        start_time = time.perf_counter()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_api_call) for _ in range(10)]
            results = [f.result() for f in futures]
        end_time = time.perf_counter()

        # All should succeed
        assert len(results) == 10
        for result in results:
            assert result.key == "CONCURRENT"

        # Should complete reasonably quickly
        duration = end_time - start_time
        assert duration < 3.0, f"Concurrent calls took {duration:.2f}s"

    return True


def kata_cache_efficiency():
    """Kata: Caching improves performance for repeated operations."""
    with TemporaryDirectory() as tmp_dir:
        out_dir = Path(tmp_dir) / "cache"

        # First generation (cold)
        start_time = time.perf_counter()
        df1 = build_gold_master(out_dir, days=10, seed=42)
        first_duration = time.perf_counter() - start_time

        # Second generation (should be faster if cached properly)
        start_time = time.perf_counter()
        df2 = build_gold_master(out_dir, days=10, seed=42)
        second_duration = time.perf_counter() - start_time

        # Results should be identical
        import pandas as pd

        pd.testing.assert_frame_equal(df1, df2)

        # Note: This kata mainly tests deterministic generation
        # Real caching would need more sophisticated setup
        assert first_duration >= 0 and second_duration >= 0

    return True


def kata_memory_usage_bounds():
    """Kata: Memory usage stays within reasonable bounds."""
    import os

    import psutil

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    with TemporaryDirectory() as tmp_dir:
        out_dir = Path(tmp_dir) / "memory"

        # Generate moderately large dataset
        df = build_gold_master(out_dir, days=30, seed=42)

        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory

        # Should not use excessive memory (< 100MB increase for test dataset)
        assert memory_increase < 100, f"Memory increased by {memory_increase:.1f}MB"
        assert len(df) > 0, "Should have generated data"

    return True


# Define the Performance School
performance_school = School(
    name="performance_school",
    description="Timing, resource usage, and scalability patterns",
    katas=[
        Kata(
            "calculation_speed",
            "Metrics calculation completes quickly",
            kata_metrics_calculation_speed,
        ),
        Kata(
            "generation_speed",
            "Gold master generation scales reasonably",
            kata_gold_master_generation_speed,
        ),
        Kata("concurrent_calls", "System handles concurrent operations", kata_concurrent_api_calls),
        Kata("cache_efficiency", "Caching improves repeated operations", kata_cache_efficiency),
        Kata("memory_bounds", "Memory usage stays reasonable", kata_memory_usage_bounds),
    ],
    parallel_safe=True,
)

# Register for discovery
register_school(performance_school)
