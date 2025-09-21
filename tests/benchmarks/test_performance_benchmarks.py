"""
Performance benchmarks for critical paths in ledzephyr.

These benchmarks ensure the system maintains performance standards
across key operations like API calls, metrics calculation, and data processing.
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from ledzephyr.client import APIClient
from ledzephyr.config import Config
from ledzephyr.metrics import MetricsCalculator
from ledzephyr.models import ProjectMetrics, TestCaseModel
from migrate_specs.gold import build_gold_master
from migrate_specs.synth import pairwise_df


@pytest.mark.benchmark(group="metrics")
def test_benchmark_metrics_calculation(benchmark, mock_api_client):
    """Benchmark metrics calculation with typical dataset."""
    # Create realistic test data
    test_cases = []
    for i in range(100):
        test_case = TestCaseModel(
            id=f"TEST-{i}",
            key=f"TEST-{i}",
            summary=f"Test case {i}",
            project_key="PERF",
            component=f"Component{i % 5}",
            labels=["automated"] if i % 2 else ["manual"],
            assignee=f"user{i % 10}@example.com",
            source_system="zephyr" if i % 2 else "qtest",
            created=datetime.now(),
            updated=datetime.now(),
            status=["Open", "InProgress", "Done"][i % 3],
            last_execution=datetime.now() if i % 3 == 0 else None,
            execution_status="PASS" if i % 4 != 0 else "FAIL",
        )
        test_cases.append(test_case)

    mock_api_client.get_jira_project.return_value = Mock(
        key="PERF", name="Performance Test", components=["Component1", "Component2"]
    )
    mock_api_client.get_zephyr_tests.return_value = test_cases[:50]
    mock_api_client.get_qtest_tests.return_value = test_cases[50:]
    mock_api_client.get_test_executions.return_value = {}

    calculator = MetricsCalculator(mock_api_client)

    # Benchmark the calculation
    result = benchmark(calculator.calculate_metrics, "PERF", "7d")

    # Verify results
    assert result.project_key == "PERF"
    assert result.total_tests == 100
    assert result.zephyr_tests == 50
    assert result.qtest_tests == 50


@pytest.mark.benchmark(group="data")
def test_benchmark_gold_master_generation(benchmark):
    """Benchmark gold master dataset generation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_dir = Path(tmp_dir) / "benchmark"

        # Benchmark dataset generation
        df = benchmark(build_gold_master, out_dir, days=30, seed=42)

        # Verify output
        assert len(df) > 0
        assert (out_dir / "gold_master.parquet").exists()
        assert (out_dir / "gold_master.csv").exists()


@pytest.mark.benchmark(group="data")
def test_benchmark_pairwise_generation(benchmark):
    """Benchmark MECE pairwise test data generation."""
    factors = {
        "browser": ["Chrome", "Firefox", "Safari", "Edge"],
        "os": ["Windows", "macOS", "Linux"],
        "resolution": ["1920x1080", "1366x768", "1440x900"],
        "theme": ["light", "dark"],
        "locale": ["en-US", "fr-FR", "ja-JP", "de-DE"],
    }

    # Benchmark pairwise generation
    df = benchmark(pairwise_df, factors, seed=42)

    # Verify output
    assert len(df) > 0
    assert all(col in df.columns for col in factors.keys())


@pytest.mark.benchmark(group="api")
def test_benchmark_api_request_mock(benchmark):
    """Benchmark API request handling with mocked responses."""
    config = Config(
        jira_url="https://test.atlassian.net",
        jira_username="test@example.com",
        jira_api_token="test_token",
    )

    with patch.object(APIClient, "_make_request") as mock_request:
        mock_response = Mock()
        mock_response.json.return_value = {
            "key": "BENCH",
            "name": "Benchmark Project",
            "components": [{"name": f"Component{i}"} for i in range(10)],
        }
        mock_request.return_value = mock_response

        client = APIClient(config)

        # Benchmark API call
        result = benchmark(client.get_jira_project, "BENCH")

        # Verify result
        assert result.key == "BENCH"
        assert len(result.components) == 10


@pytest.mark.benchmark(group="data")
def test_benchmark_dataframe_operations(benchmark):
    """Benchmark pandas DataFrame operations typical in metrics calculation."""
    # Create large dataset
    np.random.seed(42)
    data = {
        "id": [f"TEST-{i}" for i in range(1000)],
        "status": np.random.choice(["Open", "InProgress", "Done"], 1000),
        "priority": np.random.choice(["P1", "P2", "P3"], 1000),
        "component": np.random.choice([f"Component{i}" for i in range(10)], 1000),
        "execution_count": np.random.randint(0, 100, 1000),
        "pass_count": np.random.randint(0, 50, 1000),
        "fail_count": np.random.randint(0, 50, 1000),
    }
    df = pd.DataFrame(data)

    def process_dataframe(df):
        """Typical DataFrame processing operations."""
        # Group by component
        component_stats = df.groupby("component").agg(
            {
                "id": "count",
                "execution_count": "sum",
                "pass_count": "sum",
                "fail_count": "sum",
            }
        )

        # Calculate pass rate
        component_stats["pass_rate"] = (
            component_stats["pass_count"]
            / (component_stats["pass_count"] + component_stats["fail_count"])
        ).fillna(0)

        # Filter and sort
        active_components = component_stats[component_stats["id"] > 10]
        sorted_components = active_components.sort_values("pass_rate", ascending=False)

        return sorted_components

    # Benchmark DataFrame operations
    result = benchmark(process_dataframe, df)

    # Verify result
    assert len(result) > 0
    assert "pass_rate" in result.columns


@pytest.mark.benchmark(group="serialization")
def test_benchmark_json_serialization(benchmark):
    """Benchmark JSON serialization of metrics results."""
    import json

    from ledzephyr.models import TeamMetrics, TeamSource

    # Create complex metrics object
    team_metrics = []
    for i in range(20):
        team = TeamMetrics(
            team_name=f"Team{i}",
            total_tests=100 + i * 10,
            zephyr_tests=50 + i * 5,
            qtest_tests=50 + i * 5,
            adoption_ratio=0.5 + i * 0.01,
            active_users=5 + i,
        )
        team_metrics.append(team)

    metrics = ProjectMetrics(
        project_key="BENCH",
        time_window="7d",
        total_tests=2000,
        zephyr_tests=1000,
        qtest_tests=1000,
        adoption_ratio=0.5,
        active_users=100,
        coverage_parity=0.85,
        team_source=TeamSource.COMPONENT,
        teams=team_metrics,
    )

    # Benchmark JSON serialization
    json_str = benchmark(lambda: json.dumps(metrics.model_dump(), indent=2))

    # Verify output
    assert len(json_str) > 0
    data = json.loads(json_str)
    assert data["project_key"] == "BENCH"
    assert len(data["teams"]) == 20


@pytest.mark.benchmark(group="parallel")
def test_benchmark_concurrent_operations(benchmark):
    """Benchmark concurrent API operations."""
    import time
    from concurrent.futures import ThreadPoolExecutor

    def simulate_api_call(index):
        """Simulate an API call with small delay."""
        time.sleep(0.001)  # 1ms simulated network delay
        return {
            "id": f"TEST-{index}",
            "status": "Done",
            "execution_count": index * 10,
        }

    def run_concurrent_calls(count=50):
        """Run multiple API calls concurrently."""
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(simulate_api_call, i) for i in range(count)]
            results = [f.result() for f in futures]
        return results

    # Benchmark concurrent operations
    results = benchmark(run_concurrent_calls, 50)

    # Verify results
    assert len(results) == 50
    assert all(r["id"].startswith("TEST-") for r in results)


@pytest.mark.benchmark(group="cache")
def test_benchmark_cache_operations(benchmark):
    """Benchmark cache read/write operations."""
    import tempfile

    from ledzephyr.cache import SimpleAPICache

    with tempfile.TemporaryDirectory() as tmp_dir:
        cache = SimpleAPICache(cache_dir=tmp_dir)

        # Prepare test data
        test_url = "https://api.example.com/test"
        test_headers = {"Authorization": "Bearer token"}
        test_data = {"results": [{"id": i, "data": f"test{i}"} for i in range(100)]}

        # Mock the session to return our test data
        with patch.object(cache.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = test_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            def cache_operation():
                # Write to cache
                result = cache.get_cached_response(test_url, test_headers)
                # Read from cache (should be faster)
                cached = cache.get_cached_response(test_url, test_headers)
                return cached

            # Benchmark cache operations
            result = benchmark(cache_operation)

            # Verify result
            assert result is not None
            assert "results" in result
            assert len(result["results"]) == 100


# Performance regression tests with thresholds
@pytest.mark.benchmark(
    group="regression",
    min_rounds=5,
    max_time=1.0,
    min_time=0.001,
    timer="perf_counter",
    warmup=True,
)
def test_performance_regression_metrics_calculation(benchmark):
    """Ensure metrics calculation doesn't regress beyond threshold."""
    mock_client = Mock()
    mock_client.get_jira_project.return_value = Mock(key="REG", name="Regression Test")
    mock_client.get_zephyr_tests.return_value = []
    mock_client.get_qtest_tests.return_value = []
    mock_client.get_test_executions.return_value = {}

    calculator = MetricsCalculator(mock_client)

    stats = benchmark(calculator.calculate_metrics, "REG", "7d")

    # Performance assertions (adjust thresholds based on your requirements)
    assert benchmark.stats["mean"] < 0.1, "Metrics calculation should complete in < 100ms"
    assert benchmark.stats["stddev"] < 0.02, "Performance should be consistent"


if __name__ == "__main__":
    # Run benchmarks from command line
    pytest.main([__file__, "--benchmark-only", "-v"])
