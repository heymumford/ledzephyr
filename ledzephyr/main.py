#!/usr/bin/env python3
"""
LedZephyr - Lean implementation in ~280 lines.
Tracks Zephyr Scale to qTest migration metrics.
"""

import json
import logging
import logging.handlers
import os
import statistics
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import click
import httpx
from rich.console import Console
from rich.table import Table

console = Console()

# === Constants (No Magic Numbers) ===
DEFAULT_RETRY_COUNT = 3
DEFAULT_API_TIMEOUT_SECONDS = 30
MAX_API_RESULTS_ZEPHYR = 1000
MAX_API_RESULTS_JIRA = 100
MAX_API_RESULTS_QTEST = 999
DAYS_IN_SIX_MONTHS = 180
DEFAULT_HISTORY_DAYS = 30
RECENT_HISTORY_LIMIT = 7
LAST_FIVE_DAYS = 5

# === Logging Configuration ===
APPLICATION_NAME = "ledzephyr"
DEFAULT_LOG_DIR = "/var/log/ledzephyr"
FALLBACK_LOG_DIR = "./logs"
LOG_FORMAT = (
    "%(asctime)s [%(levelname)8s] %(name)s[%(process)d] txn_id:%(txn_id)s - %(message)s"
)
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Global transaction ID for request correlation (set per execution)
transaction_id: str = ""


# === Data Models ===


@dataclass
class APIResponse:
    """Container for API call results."""

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None


# === Logging Setup ===


def setup_logging(
    level: str = "INFO",
    enable_logging: bool = True,
    trace_mode: bool = False,
    txn_id: str = "",
) -> logging.Logger:
    """Setup lean Linux-standard logging with transaction tracing."""
    logger = logging.getLogger(APPLICATION_NAME)

    if not enable_logging:
        logger.disabled = True
        return logger

    # Clear any existing handlers
    logger.handlers.clear()

    # Set log level
    if trace_mode:
        level = "DEBUG"
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Try system log directory first, fallback to local
    log_dir = Path(DEFAULT_LOG_DIR)
    if not log_dir.exists() or not os.access(log_dir.parent, os.W_OK):
        log_dir = Path(FALLBACK_LOG_DIR)

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{APPLICATION_NAME}.log"

    # File handler with rotation
    handler = logging.FileHandler(log_file)

    # Custom formatter with transaction ID
    class TransactionFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            record.txn_id = txn_id
            return super().format(record)

    formatter = TransactionFormatter(LOG_FORMAT, LOG_DATE_FORMAT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# === API Client ===


def try_api_call(
    url: str, headers: Dict[str, str], params: Optional[Dict[str, Any]] = None
) -> APIResponse:
    """Single API call attempt."""
    try:
        response = httpx.get(
            url, headers=headers, params=params, timeout=DEFAULT_API_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return APIResponse(success=True, data=response.json())
    except Exception as e:
        return APIResponse(success=False, error=e)


def fetch_api_data(
    url: str, headers: Dict[str, str], params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generic API fetcher with flattened retry logic."""
    logger = logging.getLogger(APPLICATION_NAME)
    logger.info(f"API_CALL: {url}")

    for attempt in range(DEFAULT_RETRY_COUNT):
        response = try_api_call(url, headers, params)
        if response.success:
            logger.info(f"API_RESPONSE: {url} - Status: 200")
            return response.data or {}

        if attempt == DEFAULT_RETRY_COUNT - 1:
            logger.error(f"API_FAILED: {url} - All retries exhausted: {response.error}")
            console.print(f"[red]API error: {response.error}[/red]")
            return {}

        logger.warning(
            f"API_RETRY: {url} - Attempt {attempt + 1}/{DEFAULT_RETRY_COUNT} - "
            f"Error: {response.error}"
        )
        console.print(f"[yellow]Retry {attempt + 1}/{DEFAULT_RETRY_COUNT}...[/yellow]")

    return {}


def fetch_test_data_from_zephyr(
    project: str, jira_url: str, token: str
) -> List[Dict[str, Any]]:
    """Fetch test cases from Zephyr Scale (last 6 months only)."""
    url = f"{jira_url}/rest/atm/1.0/testcase/search"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "query": f'projectKey = "{project}" AND updatedDate >= now(-6m)',
        "maxResults": MAX_API_RESULTS_ZEPHYR,
        "fields": "key,name,status,createdOn,updatedOn,owner",
    }
    data = fetch_api_data(url, headers, params)
    return data.get("results", [])  # type: ignore[no-any-return]


def find_project_id(projects: Any, target_name: str) -> Optional[str]:
    """Find project ID by name."""
    if not isinstance(projects, list):
        return None

    for project in projects:
        if isinstance(project, dict) and project.get("name") == target_name:
            return project.get("id")
    return None


def fetch_test_data_from_qtest(
    project: str, qtest_url: str, token: str
) -> List[Dict[str, Any]]:
    """Fetch test cases from qTest (last 6 months only)."""
    headers = {"Authorization": f"Bearer {token}"}

    # Get project list
    projects = fetch_api_data(f"{qtest_url}/api/v3/projects", headers)
    project_id = find_project_id(projects, project)

    if not project_id:
        return []

    # Calculate 6 months ago
    six_months_ago = (datetime.now() - timedelta(days=DAYS_IN_SIX_MONTHS)).isoformat()

    # Get test cases with date filter
    params = {
        "pageSize": MAX_API_RESULTS_QTEST,
        "includeTotalCount": "true",
        "lastModifiedStartDate": six_months_ago,
    }

    data = fetch_api_data(
        f"{qtest_url}/api/v3/projects/{project_id}/test-cases", headers, params
    )
    return data if isinstance(data, list) else []


def fetch_defect_data_from_jira(
    project: str, jira_url: str, token: str
) -> List[Dict[str, Any]]:
    """Fetch defects/bugs from Jira (last 6 months only)."""
    url = f"{jira_url}/rest/api/3/search"
    headers = {"Authorization": f"Bearer {token}"}
    jql = f'project = "{project}" AND updated >= -6m AND issuetype in (Bug, Defect)'
    params = {
        "jql": jql,
        "fields": "summary,status,created,updated,assignee",
        "maxResults": MAX_API_RESULTS_JIRA,
    }
    data = fetch_api_data(url, headers, params)
    return data.get("issues", [])  # type: ignore[no-any-return]


# === Storage ===


def store_snapshot(
    data: Union[Dict[str, Any], List[Dict[str, Any]]], project: str, source: str
) -> Path:
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


def load_snapshots(
    project: str, source: str, days: int = DEFAULT_HISTORY_DAYS
) -> List[Dict[str, Any]]:
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


# === Metrics Calculation ===


def calculate_metrics(
    zephyr_data: List[Dict[str, Any]], qtest_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
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


# === Trend Analysis ===


def analyze_trends_from_data(
    zephyr_data: List[Dict[str, Any]], qtest_data: List[Dict[str, Any]], days: int = 30
) -> Dict[str, Any]:
    """Analyze migration trends from provided data (pure function).

    TODO: This is currently a stub that returns placeholder data.
    For real trend analysis with historical data, use analyze_trends() instead,
    or enhance this function to accept historical snapshots as parameters.
    """
    # For now, return a simple trend based on current data
    # In a full implementation, this would use historical snapshots
    current_metrics = calculate_metrics(zephyr_data, qtest_data)

    return {
        "trend": "→",  # Placeholder - would need historical data for real trend
        "current_rate": current_metrics["adoption_rate"],
        "average_rate": current_metrics["adoption_rate"],
        "daily_change": 0.0,
        "days_to_complete": None,
        "completion_date": None,
        "recent_history": [],
        "status": "Current snapshot only",
    }


def analyze_trends(project: str, days: int = 30) -> Dict[str, Any]:
    """Analyze migration trends from historical data."""
    zephyr_history = load_snapshots(project, "zephyr", days)
    qtest_history = load_snapshots(project, "qtest", days)

    if not zephyr_history or not qtest_history:
        return {"status": "Insufficient historical data"}

    # Calculate daily metrics
    daily_metrics = []
    for z_snap, q_snap in zip(zephyr_history, qtest_history, strict=False):
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
        "recent_history": daily_metrics[-RECENT_HISTORY_LIMIT:],  # Last 7 days
    }


# === Report Generation ===


def generate_report(
    project: str, metrics: Dict[str, Any], trends: Dict[str, Any]
) -> None:
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
        console.print("\n[bold]Trend Analysis[/bold]")
        console.print(f"Direction: {trends['trend']}")
        console.print(f"Current Rate: {trends['current_rate']:.1%}")
        console.print(f"Average Rate: {trends['average_rate']:.1%}")

        if trends["completion_date"]:
            console.print(
                f"Estimated Completion: {trends['completion_date']} "
                f"({trends['days_to_complete']} days)"
            )

        if trends.get("recent_history"):
            console.print("\n[bold]Recent History[/bold]")
            for day in trends["recent_history"][-LAST_FIVE_DAYS:]:
                console.print(f"  {day['date']}: {day['adoption_rate']:.1%}")


# === Data Models ===


@dataclass
class ProjectData:
    """Container for all project data from external APIs."""

    zephyr: List[Dict[str, Any]]
    qtest: List[Dict[str, Any]]
    jira: List[Dict[str, Any]]


# === Data Collection ===


def fetch_all_data(
    project: str,
    jira_url: str,
    jira_token: str,
    qtest_url: str,
    qtest_token: Optional[str],
) -> ProjectData:
    """Fetch all data from external APIs."""
    return ProjectData(
        zephyr=fetch_test_data_from_zephyr(project, jira_url, jira_token),
        qtest=(
            fetch_test_data_from_qtest(project, qtest_url, qtest_token)
            if qtest_token
            else []
        ),
        jira=fetch_defect_data_from_jira(project, jira_url, jira_token),
    )


def build_metrics_pipeline(
    data: ProjectData, days: int
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Pure computation pipeline for metrics and trends."""
    metrics = calculate_metrics(data.zephyr, data.qtest)
    trends = analyze_trends_from_data(data.zephyr, data.qtest, days)
    return metrics, trends


# === Credential Management ===


def get_jira_credentials() -> tuple[str, str]:
    """Get Jira credentials with single source of truth."""
    jira_url = (
        os.getenv("LEDZEPHYR_ATLASSIAN_URL")
        or os.getenv("LEDZEPHYR_JIRA_URL")
        or "https://api.atlassian.com"
    )
    jira_token = os.getenv("LEDZEPHYR_ATLASSIAN_TOKEN") or os.getenv(
        "LEDZEPHYR_JIRA_API_TOKEN"
    )

    if not jira_token:
        raise ValueError(
            "Missing required environment variable: "
            "LEDZEPHYR_ATLASSIAN_TOKEN or LEDZEPHYR_JIRA_API_TOKEN"
        )

    return jira_url, jira_token


# === CLI ===


@click.command()
@click.option("--project", "-p", required=True, help="Jira project key")
@click.option("--fetch/--no-fetch", default=True, help="Fetch fresh data from APIs")
@click.option(
    "--days", "-d", default=DEFAULT_HISTORY_DAYS, help="Days of history to analyze"
)
@click.option("--save/--no-save", default=True, help="Save snapshots to disk")
@click.option(
    "--log-level",
    default="INFO",
    help="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
)
@click.option("--no-logging", is_flag=True, help="Disable logging completely")
@click.option("--trace", is_flag=True, help="Enable trace mode (DEBUG level)")
def main(
    project: str,
    fetch: bool,
    days: int,
    save: bool,
    log_level: str,
    no_logging: bool,
    trace: bool,
) -> None:
    """LedZephyr - Zephyr Scale to qTest migration metrics."""

    # Generate new transaction ID for this execution
    global transaction_id
    transaction_id = str(uuid.uuid4())[:8]

    # Setup logging first
    logger = setup_logging(
        level=log_level,
        enable_logging=not no_logging,
        trace_mode=trace,
        txn_id=transaction_id,
    )

    logger.info(
        f"LedZephyr started - Project: {project}, Transaction: {transaction_id}"
    )

    # Get credentials from environment
    try:
        jira_url, jira_token = get_jira_credentials()
    except ValueError as e:
        logger.error(str(e))
        console.print(f"[red]Error: {e}[/red]")
        return

    qtest_url = os.getenv("LEDZEPHYR_QTEST_URL", "https://api.qtest.com")
    qtest_token = os.getenv("LEDZEPHYR_QTEST_TOKEN")

    logger.debug(f"Jira URL: {jira_url}")
    logger.debug("Credentials loaded successfully")

    if fetch:
        # Fetch fresh data
        logger.info("Starting data fetch operations")
        console.print(f"[cyan]Fetching data for {project}...[/cyan]")

        data = fetch_all_data(project, jira_url, jira_token, qtest_url, qtest_token)
        logger.info(
            f"Fetched {len(data.zephyr)} Zephyr, {len(data.qtest)} qTest test cases"
        )

        if save:
            # Store snapshots
            logger.debug("Storing data snapshots")
            z_path = store_snapshot(data.zephyr, project, "zephyr")
            store_snapshot(data.qtest, project, "qtest")
            logger.info(f"Snapshots saved to {z_path.parent.parent}")
            console.print(f"[green]Data saved to {z_path.parent.parent}[/green]")
    else:
        # Load latest snapshots
        logger.info("Loading cached data snapshots")
        zephyr_history = load_snapshots(project, "zephyr", 1)
        qtest_history = load_snapshots(project, "qtest", 1)

        if not zephyr_history or not qtest_history:
            logger.warning("No cached data available")
            console.print("[red]No recent data. Run with --fetch[/red]")
            return

        data = ProjectData(
            zephyr=zephyr_history[-1].get("data", []),
            qtest=qtest_history[-1].get("data", []),
            jira=[],
        )
        logger.info(
            f"Loaded cached data: {len(data.zephyr)} Zephyr, {len(data.qtest)} qTest"
        )

    # Build metrics pipeline (pure computation)
    logger.debug("Building metrics pipeline")
    metrics, trends = build_metrics_pipeline(data, days)
    logger.info(
        f"Metrics calculated - Adoption rate: {metrics.get('adoption_rate', 0):.1%}"
    )

    # Generate report
    logger.info("Generating migration report")
    generate_report(project, metrics, trends)
    logger.info(f"LedZephyr completed successfully - Transaction: {transaction_id}")


if __name__ == "__main__":
    main()
