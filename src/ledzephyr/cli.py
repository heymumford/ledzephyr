"""Main CLI application using Typer."""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from ledzephyr import __version__
from ledzephyr.adoption_metrics import DailySnapshot, TeamInventory, User
from ledzephyr.adoption_report import AdoptionReportGenerator
from ledzephyr.client import APIClient
from ledzephyr.config import load_config
from ledzephyr.exporters import DataExporter
from ledzephyr.metrics import MetricsCalculator
from ledzephyr.models import ProjectMetrics, TeamSource
from ledzephyr.observability import get_observability, init_observability

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
        bool,
        typer.Option("--version", callback=version_callback, help="Show version and exit"),
    ] = False,
) -> None:
    """ledzephyr (lz) - CLI tool to report Zephyr Scale → qTest migration metrics."""
    # Initialize observability
    import os

    environment = os.getenv("ENVIRONMENT", "development")
    otlp_endpoint = os.getenv("OTLP_ENDPOINT")
    init_observability(
        service_name="ledzephyr-cli",
        environment=environment,
        otlp_endpoint=otlp_endpoint,
        enable_tracing=environment != "development",
        enable_metrics=True,
    )


@app.command()
def doctor() -> None:
    """Check API connectivity and configuration."""
    console.print("🩺 [bold blue]ledzephyr doctor[/bold blue] - Checking API connectivity...")
    obs = get_observability()

    with obs.correlation_context():
        obs.log("info", "Running doctor command")

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
            obs.log("info", "Doctor check completed successfully")

        except Exception as e:
            console.print(f"❌ Error during doctor check: {e}")
            obs.log("error", "Doctor check failed", error=str(e), exc_info=True)
            raise typer.Exit(1) from e


@app.command()
def metrics(
    project: Annotated[str, typer.Option("-p", "--project", help="Jira project key")],
    windows: Annotated[
        Optional[list[str]],  # noqa: UP007
        typer.Option("-w", "--window", help="Time windows (e.g., 24h, 7d, 30d)"),
    ] = None,
    teams_source: Annotated[
        TeamSource, typer.Option("--teams-source", help="Source for team identification")
    ] = TeamSource.COMPONENT,
    output_format: Annotated[str, typer.Option("--format", help="Output format")] = "table",
    output: Annotated[
        Optional[Path], typer.Option("-o", "--out", help="Output file path")  # noqa: UP007
    ] = None,
) -> None:
    """Generate migration metrics for a Jira project."""
    if windows is None:
        windows = ["7d", "30d"]
    console.print(f"📊 [bold blue]Generating metrics for project: {project}[/bold blue]")
    obs = get_observability()

    with obs.correlation_context():
        obs.log("info", "Starting metrics generation", project=project, windows=windows)

        try:
            config = load_config()
            client = APIClient(config)
            calculator = MetricsCalculator(client)

            # Calculate metrics for each time window
            all_metrics = {}
            for window in windows:
                console.print(f"Calculating metrics for {window} window...")
                metrics = calculator.calculate_metrics(
                    project_key=project, time_window=window, teams_source=teams_source
                )
                all_metrics[window] = metrics

            # Format and display results
            if output_format == "table":
                display_table(all_metrics)
                # Save to file if specified
                if output:
                    exporter = DataExporter()
                    if output.suffix == ".xlsx":
                        exporter.export(all_metrics, output, format="excel")
                    elif output.suffix == ".pdf":
                        exporter.export(all_metrics, output, format="pdf")
                    elif output.suffix == ".html":
                        exporter.export(all_metrics, output, format="html")
                    else:
                        save_csv(all_metrics, output)
                    console.print(f"📄 Results saved to: {output}")
            elif output_format == "json":
                display_json(all_metrics, output)
            elif output_format in ["excel", "pdf", "html", "csv"]:
                if not output:
                    output = Path(
                        f"metrics_{project}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{output_format}"
                    )
                exporter = DataExporter()
                exported_path = exporter.export(all_metrics, output, format=output_format)
                console.print(f"📄 Results exported to: {exported_path}")
            else:
                console.print(f"❌ Unsupported format: {output_format}")
                raise typer.Exit(1)

            obs.log("info", "Metrics generation completed", project=project)
            obs.record_metric("metrics_command_success", 1, labels={"project": project})

        except Exception as e:
            console.print(f"❌ Error generating metrics: {e}")
            obs.log(
                "error", "Metrics generation failed", project=project, error=str(e), exc_info=True
            )
            obs.record_metric(
                "metrics_command_failure", 1, labels={"project": project, "error": type(e).__name__}
            )
            raise typer.Exit(1) from e


def display_table(metrics_data: dict[str, ProjectMetrics]) -> None:
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


def display_json(
    metrics_data: dict[str, ProjectMetrics],
    output: Optional[Path],  # noqa: UP007
) -> None:
    """Display metrics in JSON format."""
    json_data = {window: metrics.model_dump() for window, metrics in metrics_data.items()}

    if output:
        with open(output, "w") as f:
            json.dump(json_data, f, indent=2, default=str)
    else:
        console.print(json.dumps(json_data, indent=2, default=str))


def save_csv(metrics_data: dict[str, ProjectMetrics], output: Path) -> None:
    """Save metrics to CSV file."""
    with open(output, "w", newline="") as csvfile:
        fieldnames = [
            "window",
            "total_tests",
            "zephyr_tests",
            "qtest_tests",
            "adoption_ratio",
            "active_users",
            "coverage_parity",
            "defect_link_rate",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for window, metrics in metrics_data.items():
            row = {
                "window": window,
                "total_tests": metrics.total_tests,
                "zephyr_tests": metrics.zephyr_tests,
                "qtest_tests": metrics.qtest_tests,
                "adoption_ratio": metrics.adoption_ratio,
                "active_users": metrics.active_users,
                "coverage_parity": metrics.coverage_parity,
                "defect_link_rate": metrics.defect_link_rate,
            }
            writer.writerow(row)


@app.command()
def monitor(
    port: Annotated[int, typer.Option("--port", help="Port to run monitoring server on")] = 8080,
    host: Annotated[str, typer.Option("--host", help="Host to bind to")] = "0.0.0.0",
) -> None:
    """Start the monitoring API server with health checks and metrics."""
    console.print(f"🚀 [bold blue]Starting monitoring server on {host}:{port}[/bold blue]")
    console.print(f"📊 Metrics endpoint: http://localhost:{port}/metrics")
    console.print(f"🩺 Health endpoint: http://localhost:{port}/health")
    console.print("\nPress Ctrl+C to stop the server\n")

    try:
        from ledzephyr.monitoring_api import run_monitoring_server

        run_monitoring_server(host=host, port=port, reload=False)
    except KeyboardInterrupt:
        console.print("\n👋 Monitoring server stopped")
    except Exception as e:
        console.print(f"❌ Error running monitoring server: {e}")
        raise typer.Exit(1) from e


@app.command()
def adoption(
    output_format: Annotated[str, typer.Option("--format", help="Output format")] = "markdown",
    output_dir: Annotated[str, typer.Option("--output", help="Output directory")] = "reports",
    sample_data: Annotated[bool, typer.Option("--sample", help="Use sample data for demo")] = False,
) -> None:
    """Generate daily adoption and training target report."""
    import random
    from datetime import date, timedelta

    console.print("📊 [bold blue]Generating Adoption & Training Target Report[/bold blue]")

    # Create report generator
    generator = AdoptionReportGenerator(output_dir=output_dir)

    if sample_data:
        # Generate sample data for demo
        console.print("🔄 Using sample data for demonstration...")

        # Sample team inventories
        teams = ["Platform", "API", "Frontend", "Mobile", "QA", "DevOps", "Data", "Security"]
        inventories = []
        for team in teams:
            total = random.randint(100, 500)
            migrated = random.randint(int(total * 0.2), int(total * 0.8))
            inventories.append(
                TeamInventory(
                    team=team,
                    total_tests=total,
                    migrated_tests=migrated,
                    as_of_date=date.today(),
                    baseline_requirements=random.randint(20, 100),
                    qtest_requirements=random.randint(15, 90),
                    zephyr_executions=random.randint(100, 1000),
                    qtest_executions=random.randint(50, 800),
                )
            )

        # Sample users
        users = []
        for i in range(30):
            users.append(
                User(
                    email=f"user{i}@example.com",
                    name=f"User {i}",
                    executions=random.randint(5, 500),
                    role=random.choice(["tester", "lead", "viewer"]),
                )
            )

        # Sample history
        history = []
        for i in range(4):
            week_date = date.today() - timedelta(weeks=3 - i)
            history.append(DailySnapshot(date=week_date, migrated=100 * (i + 1), total=2000))

        # Sample training history
        training_history = []

    else:
        # In production, would pull from actual sources
        console.print("❌ Production data sources not yet configured. Use --sample for demo.")
        raise typer.Exit(1)

    # Generate report
    report = generator.generate_daily_report(
        inventories=inventories, users=users, history=history, training_history=training_history
    )

    # Save report
    filepath = generator.save_report(report, format=output_format)
    console.print(f"✅ Report saved to: {filepath}")

    # Display summary
    console.print("\n[bold]Report Summary:[/bold]")
    console.print(f"📈 Overall Adoption: {report.org_metrics['adoption_rate']}%")
    console.print(
        f"📊 Tests Migrated: {report.org_metrics['migrated_tests']:,} / {report.org_metrics['total_tests']:,}"
    )
    console.print(f"🚀 Velocity Trend: {report.velocity_metrics['trend']}")

    if report.completion_prediction["estimated_date"] != "Unknown":
        console.print(f"📅 Estimated Completion: {report.completion_prediction['estimated_date']}")

    console.print("\n[bold]Top Training Targets:[/bold]")
    for i, rec in enumerate(report.training_recommendations[:3], 1):
        console.print(f"{i}. {rec['team']} - Priority: {rec['priority_score']:.2f}")


if __name__ == "__main__":
    app()
