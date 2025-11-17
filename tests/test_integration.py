#!/usr/bin/env python3
"""Integration tests for LedZephyr - full pipeline testing with mocked APIs.

These tests verify that components work together correctly in the full
data collection and analysis pipeline.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from ledzephyr.main import (
    analyze_trends,
    fetch_all_data,
    generate_report,
    get_jira_credentials,
    load_snapshots,
    store_snapshot,
)


def test_full_data_collection_pipeline() -> None:
    """Integration: Full data collection from all APIs."""
    with patch("ledzephyr.main.fetch_api_data") as mock_fetch:
        # Mock responses for all three APIs
        mock_fetch.side_effect = [
            # Zephyr response
            {"results": [{"key": "Z-1", "name": "Zephyr Test 1"}]},
            # qTest project list
            [{"id": "123", "name": "TEST"}],
            # qTest test cases
            [{"id": "Q-1", "name": "qTest Test 1"}],
            # Jira issues
            {"issues": [{"key": "BUG-1", "fields": {"summary": "Bug 1"}}]},
        ]

        data = fetch_all_data(
            "TEST",
            "https://jira.example.com",
            "jira_token",
            "https://qtest.example.com",
            "qtest_token",
        )

        assert len(data.zephyr) == 1
        assert len(data.qtest) == 1
        assert len(data.jira) == 1
        assert data.zephyr[0]["key"] == "Z-1"
        assert data.qtest[0]["id"] == "Q-1"
        assert data.jira[0]["key"] == "BUG-1"


def test_data_collection_without_qtest_token() -> None:
    """Integration: Data collection when qTest token is missing."""
    with patch("ledzephyr.main.fetch_api_data") as mock_fetch:
        mock_fetch.side_effect = [
            {"results": [{"key": "Z-1"}]},  # Zephyr
            {"issues": [{"key": "BUG-1"}]},  # Jira
        ]

        data = fetch_all_data(
            "TEST",
            "https://jira.example.com",
            "jira_token",
            "https://qtest.example.com",
            None,  # No qTest token
        )

        assert len(data.zephyr) == 1
        assert len(data.qtest) == 0  # Should be empty
        assert len(data.jira) == 1


def test_storage_and_retrieval_pipeline() -> None:
    """Integration: Store and retrieve data snapshots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Store data
            zephyr_data = [{"id": "Z-1"}, {"id": "Z-2"}]
            qtest_data = [{"id": "Q-1"}]

            z_path = store_snapshot(zephyr_data, "TEST", "zephyr")
            q_path = store_snapshot(qtest_data, "TEST", "qtest")

            assert z_path.exists()
            assert q_path.exists()

            # Retrieve data
            z_snapshots = load_snapshots("TEST", "zephyr", days=30)
            q_snapshots = load_snapshots("TEST", "qtest", days=30)

            assert len(z_snapshots) == 1
            assert len(q_snapshots) == 1
            assert z_snapshots[0]["count"] == 2
            assert q_snapshots[0]["count"] == 1
            assert z_snapshots[0]["data"] == zephyr_data
            assert q_snapshots[0]["data"] == qtest_data

        finally:
            os.chdir(original_cwd)


def test_metrics_to_report_pipeline() -> None:
    """Integration: Calculate metrics and generate report."""
    with patch("ledzephyr.main.console") as mock_console:
        from ledzephyr.main import calculate_metrics

        zephyr_data = [{"id": f"Z-{i}"} for i in range(60)]
        qtest_data = [{"id": f"Q-{i}"} for i in range(40)]

        metrics = calculate_metrics(zephyr_data, qtest_data)
        trends = {
            "trend": "↑",
            "current_rate": 0.4,
            "average_rate": 0.35,
            "daily_change": 0.01,
            "days_to_complete": 60,
            "completion_date": "2025-03-15",
            "recent_history": [
                {"date": "2025-01-15", "adoption_rate": 0.35, "total": 100},
                {"date": "2025-01-16", "adoption_rate": 0.40, "total": 100},
            ],
        }

        # Generate report (shouldn't raise errors)
        generate_report("TEST", metrics, trends)

        # Verify console was called
        assert mock_console.print.called


def test_trend_analysis_with_historical_data() -> None:
    """Integration: Analyze trends with historical snapshots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            project = "TEST"

            # Create historical snapshots showing migration progress
            from datetime import datetime, timedelta

            now = datetime.now()
            for day in range(5):
                z_dir = Path(f"data/{project}/zephyr")
                q_dir = Path(f"data/{project}/qtest")
                z_dir.mkdir(parents=True, exist_ok=True)
                q_dir.mkdir(parents=True, exist_ok=True)

                z_count = 100 - (day * 10)
                q_count = day * 10

                # Create timestamps within the last 5 days
                timestamp = now - timedelta(days=4 - day)
                timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

                z_file = z_dir / f"{timestamp_str}_z.json"
                q_file = q_dir / f"{timestamp_str}_q.json"

                with open(z_file, "w") as f:
                    json.dump(
                        {
                            "timestamp": timestamp.isoformat(),
                            "project": project,
                            "source": "zephyr",
                            "count": z_count,
                            "data": [{"id": f"Z-{i}"} for i in range(z_count)],
                        },
                        f,
                    )

                with open(q_file, "w") as f:
                    json.dump(
                        {
                            "timestamp": timestamp.isoformat(),
                            "project": project,
                            "source": "qtest",
                            "count": q_count,
                            "data": [{"id": f"Q-{i}"} for i in range(q_count)],
                        },
                        f,
                    )

            # Analyze trends
            trends = analyze_trends(project, days=30)

            assert "trend" in trends
            assert "current_rate" in trends
            assert trends["trend"] in ["↑", "↓", "→"]

        finally:
            os.chdir(original_cwd)


def test_credential_management() -> None:
    """Integration: Get credentials from environment."""
    with patch.dict(
        os.environ,
        {
            "LEDZEPHYR_ATLASSIAN_URL": "https://test.atlassian.net",
            "LEDZEPHYR_ATLASSIAN_TOKEN": "test_token",
        },
    ):
        url, token = get_jira_credentials()

        assert url == "https://test.atlassian.net"
        assert token == "test_token"  # noqa: S105


def test_credential_fallback() -> None:
    """Integration: Fallback to old env var names."""
    with patch.dict(
        os.environ,
        {
            "LEDZEPHYR_JIRA_URL": "https://jira.example.com",
            "LEDZEPHYR_JIRA_API_TOKEN": "jira_token",
        },
        clear=True,
    ):
        url, token = get_jira_credentials()

        assert url == "https://jira.example.com"
        assert token == "jira_token"  # noqa: S105


def test_credential_missing_raises_error() -> None:
    """Integration: Missing credentials should raise ValueError."""
    with patch.dict(os.environ, {}, clear=True):
        try:
            get_jira_credentials()
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "Missing required environment variable" in str(e)


def test_error_handling_pipeline() -> None:
    """Integration: Pipeline handles API errors gracefully."""
    with patch("ledzephyr.main.fetch_api_data") as mock_fetch:
        # All API calls fail
        mock_fetch.return_value = {}

        data = fetch_all_data(
            "TEST",
            "https://jira.example.com",
            "token",
            "https://qtest.example.com",
            "token",
        )

        # Should return empty lists, not crash
        assert data.zephyr == []
        assert data.qtest == []
        assert data.jira == []


def test_snapshot_with_empty_data() -> None:
    """Integration: Store and load empty snapshots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Store empty data
            path = store_snapshot([], "TEST", "zephyr")
            assert path.exists()

            # Retrieve empty data
            snapshots = load_snapshots("TEST", "zephyr", days=30)
            assert len(snapshots) == 1
            assert snapshots[0]["count"] == 0
            assert snapshots[0]["data"] == []

        finally:
            os.chdir(original_cwd)


def test_multiple_projects_isolation() -> None:
    """Integration: Multiple projects store data independently."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Store data for two projects
            store_snapshot([{"id": "A-1"}], "PROJECT_A", "zephyr")
            store_snapshot([{"id": "B-1"}], "PROJECT_B", "zephyr")

            # Retrieve data independently
            a_snapshots = load_snapshots("PROJECT_A", "zephyr", days=30)
            b_snapshots = load_snapshots("PROJECT_B", "zephyr", days=30)

            assert len(a_snapshots) == 1
            assert len(b_snapshots) == 1
            assert a_snapshots[0]["data"][0]["id"] == "A-1"
            assert b_snapshots[0]["data"][0]["id"] == "B-1"

        finally:
            os.chdir(original_cwd)


def run_integration_tests() -> None:
    """Run all integration tests."""
    tests = [
        ("Full data collection", test_full_data_collection_pipeline),
        ("Collection without qTest token", test_data_collection_without_qtest_token),
        ("Storage and retrieval", test_storage_and_retrieval_pipeline),
        ("Metrics to report", test_metrics_to_report_pipeline),
        ("Trend analysis with history", test_trend_analysis_with_historical_data),
        ("Credential management", test_credential_management),
        ("Credential fallback", test_credential_fallback),
        ("Missing credentials error", test_credential_missing_raises_error),
        ("Error handling pipeline", test_error_handling_pipeline),
        ("Empty data snapshots", test_snapshot_with_empty_data),
        ("Multi-project isolation", test_multiple_projects_isolation),
    ]

    print("Running Integration Tests...")
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
    print(f"Integration Tests: {passed} passed, {failed} failed")

    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    run_integration_tests()
