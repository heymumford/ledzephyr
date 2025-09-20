"""Main CLI application using Typer."""

import csv
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from ledzephyr import __version__
from ledzephyr.config import Config, load_config
from ledzephyr.client import APIClient
from ledzephyr.models import ProjectMetrics, TeamSource
from ledzephyr.metrics import MetricsCalculator

app = typer.Typer(
    name="ledzephyr",
    help="CLI tool to report Zephyr Scale → qTest migration metrics per Jira project/team",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"ledzephyr version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=version_callback, help="Show version and exit")
    ] = None,
) -> None:
    """ledzephyr (lz) - CLI tool to report Zephyr Scale → qTest migration metrics."""
    pass


@app.command()
def doctor() -> None:
    """Check API connectivity and configuration."""
    console.print("🩺 [bold blue]ledzephyr doctor[/bold blue] - Checking API connectivity...")
    
    try:
        config = load_config()
        client = APIClient(config)
        
        # Test Jira connectivity
        console.print("Testing Jira API connection...")
        jira_status = client.test_jira_connection()
        if jira_status:
            console.print("✅ Jira API: Connected")
        else:
            console.print("❌ Jira API: Connection failed")
            
        # Test Zephyr Scale connectivity
        if config.zephyr_token:
            console.print("Testing Zephyr Scale API connection...")
            zephyr_status = client.test_zephyr_connection()
            if zephyr_status:
                console.print("✅ Zephyr Scale API: Connected")
            else:
                console.print("❌ Zephyr Scale API: Connection failed")
        else:
            console.print("⚠️  Zephyr Scale API: No token configured")
            
        # Test qTest connectivity
        if config.qtest_token:
            console.print("Testing qTest API connection...")
            qtest_status = client.test_qtest_connection()
            if qtest_status:
                console.print("✅ qTest API: Connected")
            else:
                console.print("❌ qTest API: Connection failed")
        else:
            console.print("⚠️  qTest API: No token configured")
            
        console.print("\n🎉 Doctor check complete!")
        
    except Exception as e:
        console.print(f"❌ Error during doctor check: {e}")
        raise typer.Exit(1)


@app.command()
def metrics(
    project: Annotated[str, typer.Option("-p", "--project", help="Jira project key")],
    windows: Annotated[
        List[str], 
        typer.Option("-w", "--window", help="Time windows (e.g., 24h, 7d, 30d)")
    ] = ["7d", "30d"],
    teams_source: Annotated[
        TeamSource, 
        typer.Option("--teams-source", help="Source for team identification")
    ] = TeamSource.COMPONENT,
    format: Annotated[
        str, 
        typer.Option("--format", help="Output format")
    ] = "table",
    output: Annotated[
        Optional[Path], 
        typer.Option("-o", "--out", help="Output file path")
    ] = None,
) -> None:
    """Generate migration metrics for a Jira project."""
    console.print(f"📊 [bold blue]Generating metrics for project: {project}[/bold blue]")
    
    try:
        config = load_config()
        client = APIClient(config)
        calculator = MetricsCalculator(client)
        
        # Calculate metrics for each time window
        all_metrics = {}
        for window in windows:
            console.print(f"Calculating metrics for {window} window...")
            metrics = calculator.calculate_metrics(
                project_key=project,
                time_window=window,
                teams_source=teams_source
            )
            all_metrics[window] = metrics
            
        # Format and display results
        if format == "table":
            display_table(all_metrics)
        elif format == "json":
            display_json(all_metrics, output)
        else:
            console.print(f"❌ Unsupported format: {format}")
            raise typer.Exit(1)
            
        # Save to CSV if output file specified
        if output and format != "json":
            save_csv(all_metrics, output)
            console.print(f"📄 Results saved to: {output}")
            
    except Exception as e:
        console.print(f"❌ Error generating metrics: {e}")
        raise typer.Exit(1)


def display_table(metrics_data: Dict[str, ProjectMetrics]) -> None:
    """Display metrics in a rich table format."""
    table = Table(title="Migration Metrics")
    
    table.add_column("Window", style="bold")
    table.add_column("Total Tests")
    table.add_column("Zephyr Tests")
    table.add_column("qTest Tests")
    table.add_column("Adoption Ratio")
    table.add_column("Active Users")
    table.add_column("Coverage Parity")
    table.add_column("Defect Link Rate")
    
    for window, metrics in metrics_data.items():
        table.add_row(
            window,
            str(metrics.total_tests),
            str(metrics.zephyr_tests),
            str(metrics.qtest_tests),
            f"{metrics.adoption_ratio:.2%}",
            str(metrics.active_users),
            f"{metrics.coverage_parity:.2%}",
            f"{metrics.defect_link_rate:.2%}",
        )
    
    console.print(table)


def display_json(metrics_data: Dict[str, ProjectMetrics], output: Optional[Path]) -> None:
    """Display metrics in JSON format."""
    json_data = {
        window: metrics.dict() for window, metrics in metrics_data.items()
    }
    
    if output:
        with open(output, 'w') as f:
            json.dump(json_data, f, indent=2, default=str)
    else:
        console.print(json.dumps(json_data, indent=2, default=str))


def save_csv(metrics_data: Dict[str, ProjectMetrics], output: Path) -> None:
    """Save metrics to CSV file."""
    with open(output, 'w', newline='') as csvfile:
        fieldnames = [
            'window', 'total_tests', 'zephyr_tests', 'qtest_tests',
            'adoption_ratio', 'active_users', 'coverage_parity', 'defect_link_rate'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for window, metrics in metrics_data.items():
            row = metrics.dict()
            row['window'] = window
            writer.writerow(row)


if __name__ == "__main__":
    app()