"""Tests for CLI functionality."""

import pytest
from typer.testing import CliRunner
from ledzephyr.cli import app


runner = CliRunner()


def test_cli_help():
    """Test that CLI help command works."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    # Check for presence of key terms without ANSI codes
    output = result.stdout.lower()
    assert "retrieve metrics" in output or "time windows" in output or "stubbed implementation" in output


def test_metrics_command_via_default():
    """Test metrics command as default command (since it's the only command)."""
    result = runner.invoke(app, ["-p", "test_key", "-w", "24h"])
    assert result.exit_code == 0
    # Should be stubbed implementation for now
    output = result.stdout.lower()
    assert "stubbed" in output or "not implemented" in output or "metrics command called" in output


def test_metrics_command_multiple_windows():
    """Test metrics command with multiple time windows."""
    result = runner.invoke(app, ["-p", "test_key", "-w", "24h", "-w", "7d"])
    assert result.exit_code == 0


def test_metrics_command_format_options():
    """Test metrics command with different format options."""
    # Test table format
    result = runner.invoke(app, ["-p", "test_key", "-w", "24h", "--format", "table"])
    assert result.exit_code == 0
    
    # Test json format
    result = runner.invoke(app, ["-p", "test_key", "-w", "24h", "--format", "json"])
    assert result.exit_code == 0


def test_metrics_command_missing_password():
    """Test metrics command without required password."""
    result = runner.invoke(app, ["-w", "24h"])
    assert result.exit_code != 0


def test_metrics_command_missing_windows():
    """Test metrics command without required windows."""
    result = runner.invoke(app, ["-p", "test_key"])
    assert result.exit_code != 0


def test_metrics_command_invalid_format():
    """Test metrics command with invalid format option."""
    result = runner.invoke(app, ["-p", "test_key", "-w", "24h", "--format", "xml"])
    assert result.exit_code != 0