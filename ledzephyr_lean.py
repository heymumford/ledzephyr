#!/usr/bin/env python3
"""
LedZephyr - Lean implementation in ~280 lines.
Tracks Zephyr Scale to qTest migration metrics.
"""

import json
import os
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

import click
import httpx
from rich.console import Console
from rich.table import Table

console = Console()


# === API Client (~50 lines) ===


def fetch_api_data(url: str, headers: dict, params: dict = None) -> dict:
    """Generic API fetcher with basic retry."""
    for attempt in range(3):
        try:
            response = httpx.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if attempt == 2:
                console.print(f"[red]API error: {e}[/red]")
                return {}
            console.print(f"[yellow]Retry {attempt + 1}/3...[/yellow]")
    return {}


def fetch_zephyr_tests(project: str, jira_url: str, token: str) -> List[Dict]:
    """Fetch test cases from Zephyr Scale (last 6 months only)."""
    url = f"{jira_url}/rest/atm/1.0/testcase/search"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "query": f'projectKey = "{project}" AND updatedDate >= now(-6m)',
        "maxResults": 1000,
        "fields": "key,name,status,createdOn,updatedOn,owner",
    }
    data = fetch_api_data(url, headers, params)
    return data.get("results", [])


def fetch_qtest_tests(project: str, qtest_url: str, token: str) -> List[Dict]:
    """Fetch test cases from qTest (last 6 months only)."""
    # First get project ID
    url = f"{qtest_url}/api/v3/projects"
    headers = {"Authorization": f"Bearer {token}"}
    projects = fetch_api_data(url, headers)

    project_id = None
    for p in projects:
        if p.get("name") == project:
            project_id = p.get("id")
            break

    if not project_id:
        return []

    # Calculate 6 months ago
    six_months_ago = (datetime.now() - timedelta(days=180)).isoformat()

    # Get test cases with date filter
    url = f"{qtest_url}/api/v3/projects/{project_id}/test-cases"
    params = {
        "pageSize": 999,
        "includeTotalCount": "true",
        "lastModifiedStartDate": six_months_ago,
    }
    data = fetch_api_data(url, headers, params)
    return data if isinstance(data, list) else []


def fetch_jira_defects(project: str, jira_url: str, token: str) -> List[Dict]:
    """Fetch defects/bugs from Jira (last 6 months only)."""
    url = f"{jira_url}/rest/api/3/search"
    headers = {"Authorization": f"Bearer {token}"}
    jql = f'project = "{project}" AND updated >= -6m AND issuetype in (Bug, Defect)'
    params = {
        "jql": jql,
        "fields": "summary,status,created,updated,assignee",
        "maxResults": 100,
    }
    data = fetch_api_data(url, headers, params)
    return data.get("issues", [])


# === Storage (~40 lines) ===


def store_snapshot(data: dict, project: str, source: str) -> Path:
    """Store timestamped snapshot to disk."""
    timestamp = datetime.now()
    filepath = Path(
        f"data/{project}/{source}/{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    )
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w") as f:
        json.dump(
            {
                "timestamp": timestamp.isoformat(),
                "project": project,
                "source": source,
                "count": len(data) if isinstance(data, list) else 0,
                "data": data,
            },
            f,
            indent=2,
        )

    return filepath


def load_snapshots(project: str, source: str, days: int = 30) -> List[Dict]:
    """Load historical snapshots."""
    data_dir = Path(f"data/{project}/{source}")
    if not data_dir.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    snapshots = []

    for file in sorted(data_dir.glob("*.json")):
        with open(file) as f:
            data = json.load(f)
            if datetime.fromisoformat(data["timestamp"]) > cutoff:
                snapshots.append(data)

    return snapshots


# === Metrics Calculation (~40 lines) ===


def calculate_metrics(zephyr_data: List, qtest_data: List) -> Dict[str, Any]:
    """Calculate migration metrics."""
    zephyr_count = len(zephyr_data) if isinstance(zephyr_data, list) else 0
    qtest_count = len(qtest_data) if isinstance(qtest_data, list) else 0
    total = zephyr_count + qtest_count

    if total == 0:
        return {
            "total_tests": 0,
            "zephyr_tests": 0,
            "qtest_tests": 0,
            "adoption_rate": 0,
            "status": "No test data found",
        }

    adoption_rate = qtest_count / total

    return {
        "total_tests": total,
        "zephyr_tests": zephyr_count,
        "qtest_tests": qtest_count,
        "adoption_rate": adoption_rate,
        "migration_progress": f"{adoption_rate:.1%}",
        "remaining": zephyr_count,
        "status": "Complete" if adoption_rate >= 1.0 else "In Progress",
    }


# === Trend Analysis (~50 lines) ===


def analyze_trends(project: str, days: int = 30) -> Dict[str, Any]:
    """Analyze migration trends from historical data."""
    zephyr_history = load_snapshots(project, "zephyr", days)
    qtest_history = load_snapshots(project, "qtest", days)

    if not zephyr_history or not qtest_history:
        return {"status": "Insufficient historical data"}

    # Calculate daily metrics
    daily_metrics = []
    for z_snap, q_snap in zip(zephyr_history, qtest_history):
        date = datetime.fromisoformat(z_snap["timestamp"]).date()
        metrics = calculate_metrics(z_snap.get("data", []), q_snap.get("data", []))
        daily_metrics.append(
            {
                "date": str(date),
                "adoption_rate": metrics["adoption_rate"],
                "total": metrics["total_tests"],
            }
        )

    if len(daily_metrics) < 2:
        return {"status": "Need at least 2 days of data"}

    # Calculate trend
    rates = [m["adoption_rate"] for m in daily_metrics]
    first_rate = rates[0]
    last_rate = rates[-1]
    avg_rate = statistics.mean(rates)

    # Simple linear projection
    daily_change = (last_rate - first_rate) / len(rates) if len(rates) > 1 else 0

    if daily_change > 0 and last_rate < 1.0:
        days_to_complete = int((1.0 - last_rate) / daily_change)
        completion_date = datetime.now() + timedelta(days=days_to_complete)
    else:
        days_to_complete = None
        completion_date = None

    return {
        "trend": "↑" if daily_change > 0 else "↓" if daily_change < 0 else "→",
        "current_rate": last_rate,
        "average_rate": avg_rate,
        "daily_change": daily_change,
        "days_to_complete": days_to_complete,
        "completion_date": (
            completion_date.strftime("%Y-%m-%d") if completion_date else None
        ),
        "recent_history": daily_metrics[-7:],  # Last 7 days
    }


# === Report Generation (~40 lines) ===


def generate_report(project: str, metrics: dict, trends: dict) -> None:
    """Generate and display migration report."""
    console.print(f"\n[bold blue]Migration Report: {project}[/bold blue]")
    console.print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Current state table
    table = Table(title="Current State")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Tests", f"{metrics['total_tests']:,}")
    table.add_row("Zephyr Scale", f"{metrics['zephyr_tests']:,}")
    table.add_row("qTest", f"{metrics['qtest_tests']:,}")
    table.add_row("Migration Progress", metrics["migration_progress"])
    table.add_row("Status", metrics["status"])

    console.print(table)

    # Trends
    if trends.get("current_rate") is not None:
        console.print(f"\n[bold]Trend Analysis[/bold]")
        console.print(f"Direction: {trends['trend']}")
        console.print(f"Current Rate: {trends['current_rate']:.1%}")
        console.print(f"Average Rate: {trends['average_rate']:.1%}")

        if trends["completion_date"]:
            console.print(
                f"Estimated Completion: {trends['completion_date']} ({trends['days_to_complete']} days)"
            )

        if trends.get("recent_history"):
            console.print(f"\n[bold]Recent History[/bold]")
            for day in trends["recent_history"][-5:]:
                console.print(f"  {day['date']}: {day['adoption_rate']:.1%}")


# === CLI (~50 lines) ===


@click.command()
@click.option("--project", "-p", required=True, help="Jira project key")
@click.option("--fetch/--no-fetch", default=True, help="Fetch fresh data from APIs")
@click.option("--days", "-d", default=30, help="Days of history to analyze")
@click.option("--save/--no-save", default=True, help="Save snapshots to disk")
def main(project: str, fetch: bool, days: int, save: bool):
    """LedZephyr - Zephyr Scale to qTest migration metrics."""

    # Get credentials from environment
    jira_url = os.getenv("LEDZEPHYR_JIRA_URL", "https://api.atlassian.com")
    jira_token = os.getenv("LEDZEPHYR_JIRA_API_TOKEN")
    qtest_url = os.getenv("LEDZEPHYR_QTEST_URL", "https://api.qtest.com")
    qtest_token = os.getenv("LEDZEPHYR_QTEST_TOKEN")

    if not jira_token:
        console.print("[red]Error: LEDZEPHYR_JIRA_API_TOKEN not set[/red]")
        return

    if fetch:
        # Fetch fresh data
        console.print(f"[cyan]Fetching data for {project}...[/cyan]")

        zephyr_data = fetch_zephyr_tests(project, jira_url, jira_token)
        qtest_data = (
            fetch_qtest_tests(project, qtest_url, qtest_token) if qtest_token else []
        )

        if save:
            # Store snapshots
            z_path = store_snapshot(zephyr_data, project, "zephyr")
            q_path = store_snapshot(qtest_data, project, "qtest")
            console.print(f"[green]Data saved to {z_path.parent.parent}[/green]")
    else:
        # Load latest snapshots
        zephyr_history = load_snapshots(project, "zephyr", 1)
        qtest_history = load_snapshots(project, "qtest", 1)

        if not zephyr_history or not qtest_history:
            console.print("[red]No recent data. Run with --fetch[/red]")
            return

        zephyr_data = zephyr_history[-1].get("data", [])
        qtest_data = qtest_history[-1].get("data", [])

    # Calculate metrics
    metrics = calculate_metrics(zephyr_data, qtest_data)

    # Analyze trends
    trends = analyze_trends(project, days)

    # Generate report
    generate_report(project, metrics, trends)


if __name__ == "__main__":
    main()
