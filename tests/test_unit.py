#!/usr/bin/env python3
"""Unit tests for LedZephyr - pure function testing."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ledzephyr.main import (
    APIResponse,
    ProjectData,
    analyze_trends_from_data,
    build_metrics_pipeline,
    calculate_metrics,
    find_project_id,
    load_snapshots,
    store_snapshot,
    _calculate_daily_metrics,
    _calculate_trend_vector,
    _project_completion_date,
    _build_current_state_table,
)


def test_calculate_metrics_normal_case() -> None:
    """Test metrics calculation with normal data."""
    zephyr = [{"id": f"Z-{i}"} for i in range(100)]
    qtest = [{"id": f"Q-{i}"} for i in range(75)]

    metrics = calculate_metrics(zephyr, qtest)

    assert metrics["total_tests"] == 175
    assert metrics["zephyr_tests"] == 100
    assert metrics["qtest_tests"] == 75
    assert abs(metrics["adoption_rate"] - 0.4286) < 0.001
    assert metrics["migration_progress"] == "42.9%"
    assert metrics["status"] == "In Progress"
    assert metrics["remaining"] == 100


def test_calculate_metrics_empty_data() -> None:
    """Test metrics calculation with no data."""
    metrics = calculate_metrics([], [])

    assert metrics["total_tests"] == 0
    assert metrics["zephyr_tests"] == 0
    assert metrics["qtest_tests"] == 0
    assert metrics["adoption_rate"] == 0
    assert metrics["status"] == "No test data found"


def test_calculate_metrics_complete_migration() -> None:
    """Test metrics when migration is complete."""
    zephyr: List[Dict[str, Any]] = []
    qtest = [{"id": f"Q-{i}"} for i in range(100)]

    metrics = calculate_metrics(zephyr, qtest)

    assert metrics["total_tests"] == 100
    assert metrics["adoption_rate"] == 1.0
    assert metrics["migration_progress"] == "100.0%"
    assert metrics["status"] == "Complete"


def test_calculate_metrics_no_migration_started() -> None:
    """Test metrics when no migration has started."""
    zephyr = [{"id": f"Z-{i}"} for i in range(100)]
    qtest: List[Dict[str, Any]] = []

    metrics = calculate_metrics(zephyr, qtest)

    assert metrics["total_tests"] == 100
    assert metrics["adoption_rate"] == 0.0
    assert metrics["migration_progress"] == "0.0%"
    assert metrics["status"] == "In Progress"


def test_find_project_id_success() -> None:
    """Test finding project ID by name."""
    projects = [
        {"id": "123", "name": "PROJECT_A"},
        {"id": "456", "name": "PROJECT_B"},
        {"id": "789", "name": "PROJECT_C"},
    ]

    assert find_project_id(projects, "PROJECT_A") == "123"
    assert find_project_id(projects, "PROJECT_B") == "456"
    assert find_project_id(projects, "PROJECT_C") == "789"


def test_find_project_id_not_found() -> None:
    """Test finding non-existent project."""
    projects = [{"id": "123", "name": "PROJECT_A"}]

    assert find_project_id(projects, "MISSING") is None


def test_find_project_id_invalid_input() -> None:
    """Test finding project with invalid input."""
    assert find_project_id(None, "PROJECT") is None
    assert find_project_id([], "PROJECT") is None
    assert find_project_id("not a list", "PROJECT") is None  # type: ignore[arg-type]


def test_find_project_id_malformed_projects() -> None:
    """Test finding project with malformed project list."""
    projects = [
        {"id": "123"},  # Missing name
        {"name": "PROJECT_B"},  # Missing id
        "not a dict",  # Wrong type
    ]

    assert find_project_id(projects, "PROJECT_B") is None


def test_api_response_success() -> None:
    """Test APIResponse data structure for success."""
    response = APIResponse(success=True, data={"key": "value"})

    assert response.success is True
    assert response.data == {"key": "value"}
    assert response.error is None


def test_api_response_failure() -> None:
    """Test APIResponse data structure for failure."""
    error = Exception("API error")
    response = APIResponse(success=False, error=error)

    assert response.success is False
    assert response.data is None
    assert response.error == error


def test_project_data_structure() -> None:
    """Test ProjectData dataclass."""
    zephyr = [{"id": "Z-1"}]
    qtest = [{"id": "Q-1"}]
    jira = [{"id": "JIRA-1"}]

    data = ProjectData(zephyr=zephyr, qtest=qtest, jira=jira)

    assert data.zephyr == zephyr
    assert data.qtest == qtest
    assert data.jira == jira


def test_build_metrics_pipeline() -> None:
    """Test pure metrics pipeline computation."""
    zephyr = [{"id": f"Z-{i}"} for i in range(50)]
    qtest = [{"id": f"Q-{i}"} for i in range(50)]
    data = ProjectData(zephyr=zephyr, qtest=qtest, jira=[])

    metrics, trends = build_metrics_pipeline(data, days=30)

    assert metrics["total_tests"] == 100
    assert metrics["adoption_rate"] == 0.5
    assert trends["current_rate"] == 0.5
    assert trends["trend"] == "→"  # Placeholder in stub


def test_analyze_trends_from_data_stub() -> None:
    """Test trend analysis stub function."""
    zephyr = [{"id": f"Z-{i}"} for i in range(60)]
    qtest = [{"id": f"Q-{i}"} for i in range(40)]

    trends = analyze_trends_from_data(zephyr, qtest, days=30)

    assert trends["trend"] == "→"  # Placeholder
    assert abs(trends["current_rate"] - 0.4) < 0.01
    assert trends["status"] == "Current snapshot only"


def test_store_snapshot() -> None:
    """Test storing timestamped snapshot to disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory context
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            data = [{"id": "test-1"}, {"id": "test-2"}]
            project = "TEST_PROJECT"
            source = "test_source"

            filepath = store_snapshot(data, project, source)

            assert filepath.exists()
            assert filepath.parent.name == source
            assert filepath.parent.parent.name == project

            # Verify content
            with open(filepath) as f:
                stored = json.load(f)
                assert stored["project"] == project
                assert stored["source"] == source
                assert stored["count"] == 2
                assert stored["data"] == data
                assert "timestamp" in stored

        finally:
            os.chdir(original_cwd)


def test_load_snapshots() -> None:
    """Test loading historical snapshots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            project = "TEST"
            source = "zephyr"

            # Create test snapshots with recent timestamps
            data_dir = Path(f"data/{project}/{source}")
            data_dir.mkdir(parents=True)

            # Use current datetime to ensure they're within the 30-day window

            now = datetime.now()
            for i in range(3):
                # Create snapshots with different timestamps (1 hour apart)
                timestamp = now.replace(hour=12 + i, minute=0, second=0, microsecond=0)
                snapshot_file = data_dir / f"{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
                with open(snapshot_file, "w") as f:
                    json.dump(
                        {
                            "timestamp": timestamp.isoformat(),
                            "project": project,
                            "source": source,
                            "count": i + 1,
                            "data": [{"id": f"item-{i}"}],
                        },
                        f,
                    )

            # Load snapshots (last 30 days)
            snapshots = load_snapshots(project, source, days=30)

            assert len(snapshots) == 3, f"Expected 3 snapshots, got {len(snapshots)}"
            assert all(s["project"] == project for s in snapshots)
            assert all(s["source"] == source for s in snapshots)

        finally:
            os.chdir(original_cwd)


def test_load_snapshots_no_directory() -> None:
    """Test loading snapshots when directory doesn't exist."""
    snapshots = load_snapshots("NONEXISTENT", "zephyr", days=30)
    assert snapshots == []


def test_calculate_daily_metrics() -> None:
    """Test daily metrics calculation from snapshots."""
    zephyr_snap = {"data": [{"id": f"Z-{i}"} for i in range(100)], "timestamp": "2024-01-01T00:00:00"}
    qtest_snap = {"data": [{"id": f"Q-{i}"} for i in range(40)], "timestamp": "2024-01-01T00:00:00"}

    daily_metrics = _calculate_daily_metrics(zephyr_snap, qtest_snap)

    assert daily_metrics["date"] == "2024-01-01"
    assert abs(daily_metrics["adoption_rate"] - 0.2857) < 0.001  # 40 / 140
    assert daily_metrics["total"] == 140


def test_calculate_trend_vector() -> None:
    """Test trend vector calculation from adoption rates."""
    rates = [0.10, 0.15, 0.20, 0.25, 0.30]

    trend = _calculate_trend_vector(rates)

    assert trend["trend"] == "↑"  # Positive trend
    assert trend["daily_change"] > 0
    assert abs(trend["current_rate"] - 0.30) < 0.001
    assert abs(trend["average_rate"] - 0.20) < 0.001


def test_calculate_trend_vector_flat() -> None:
    """Test flat trend detection."""
    rates = [0.50, 0.50, 0.50, 0.50, 0.50]

    trend = _calculate_trend_vector(rates)

    assert trend["trend"] == "→"  # Flat trend
    assert trend["daily_change"] == 0


def test_calculate_trend_vector_declining() -> None:
    """Test declining trend detection."""
    rates = [0.80, 0.75, 0.70, 0.65, 0.60]

    trend = _calculate_trend_vector(rates)

    assert trend["trend"] == "↓"  # Declining trend
    assert trend["daily_change"] < 0


def test_project_completion_date_linear() -> None:
    """Test completion date projection."""
    current_rate = 0.75  # 75% done
    daily_change = 0.05  # 5% per day

    completion = _project_completion_date(current_rate, daily_change)

    assert completion["days_to_complete"] == 5
    assert completion["completion_date"] is not None


def test_project_completion_date_impossible() -> None:
    """Test completion projection when impossible."""
    current_rate = 0.75  # 75% done
    daily_change = -0.05  # Declining (negative progress)

    completion = _project_completion_date(current_rate, daily_change)

    assert completion["days_to_complete"] is None
    assert completion["completion_date"] is None


def test_build_current_state_table() -> None:
    """Test current state table building."""
    metrics = {
        "total_tests": 175,
        "zephyr_tests": 100,
        "qtest_tests": 75,
        "migration_progress": "42.9%",
        "status": "In Progress"
    }

    table = _build_current_state_table(metrics)

    # Table should be created (RichTable object)
    assert table is not None
    assert hasattr(table, 'title')
    assert table.title == "Current State"


def run_unit_tests() -> None:
    """Run all unit tests."""
    tests = [
        ("Metrics calculation (normal)", test_calculate_metrics_normal_case),
        ("Metrics calculation (empty)", test_calculate_metrics_empty_data),
        ("Metrics calculation (complete)", test_calculate_metrics_complete_migration),
        (
            "Metrics calculation (not started)",
            test_calculate_metrics_no_migration_started,
        ),
        ("Find project ID (success)", test_find_project_id_success),
        ("Find project ID (not found)", test_find_project_id_not_found),
        ("Find project ID (invalid input)", test_find_project_id_invalid_input),
        ("Find project ID (malformed)", test_find_project_id_malformed_projects),
        ("APIResponse (success)", test_api_response_success),
        ("APIResponse (failure)", test_api_response_failure),
        ("ProjectData structure", test_project_data_structure),
        ("Build metrics pipeline", test_build_metrics_pipeline),
        ("Analyze trends stub", test_analyze_trends_from_data_stub),
        ("Store snapshot", test_store_snapshot),
        ("Load snapshots", test_load_snapshots),
        ("Load snapshots (no dir)", test_load_snapshots_no_directory),
        ("Calculate daily metrics", test_calculate_daily_metrics),
        ("Calculate trend vector (↑)", test_calculate_trend_vector),
        ("Calculate trend vector (→)", test_calculate_trend_vector_flat),
        ("Calculate trend vector (↓)", test_calculate_trend_vector_declining),
        ("Project completion (linear)", test_project_completion_date_linear),
        ("Project completion (impossible)", test_project_completion_date_impossible),
        ("Build current state table", test_build_current_state_table),
    ]

    print("Running Unit Tests...")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            print(f"✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name}: Unexpected error: {e}")
            failed += 1

    print("=" * 60)
    print(f"Unit Tests: {passed} passed, {failed} failed")

    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    run_unit_tests()
