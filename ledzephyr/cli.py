"""Command-line interface for ledzephyr."""

from typing import List
import typer
from enum import Enum


class OutputFormat(str, Enum):
    """Output format options."""
    table = "table"
    json = "json"


app = typer.Typer(help="A utility to measure your migration to qTest cloud.")


@app.command()
def metrics(
    password: str = typer.Option(..., "-p", "--password", help="API password/key"),
    window: List[str] = typer.Option(..., "-w", "--window", help="Time windows (e.g., 24h, 7d)"),
    format: OutputFormat = typer.Option(OutputFormat.table, "--format", help="Output format")
):
    """
    Retrieve metrics for specified time windows.
    
    This is a stubbed implementation for the first vertical slice.
    """
    typer.echo(f"Metrics command called with:")
    typer.echo(f"  Password: {password}")
    typer.echo(f"  Windows: {', '.join(window)}")
    typer.echo(f"  Format: {format.value}")
    typer.echo("\nThis is a stubbed implementation - not yet fully implemented.")
    typer.echo("Time window parsing and output formatting will be integrated in future iterations.")


if __name__ == "__main__":
    app()