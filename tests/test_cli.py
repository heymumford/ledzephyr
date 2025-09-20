"""Test CLI commands."""

import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from ledzephyr.cli import app
from ledzephyr.models import ProjectMetrics, TeamSource


runner = CliRunner()


def test_version():
    """Test version command."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "ledzephyr version" in result.stdout


def test_help():
    """Test help message."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "CLI tool to report Zephyr Scale" in result.stdout


@patch('ledzephyr.cli.load_config')
@patch('ledzephyr.cli.APIClient')
def test_doctor_command_success(mock_client_class, mock_load_config):
    """Test doctor command with successful connections."""
    # Mock configuration
    mock_config = MagicMock()
    mock_config.zephyr_token = "test-token"
    mock_config.qtest_token = "test-token"
    mock_load_config.return_value = mock_config

    # Mock client
    mock_client = MagicMock()
    mock_client.test_jira_connection.return_value = True
    mock_client.test_zephyr_connection.return_value = True
    mock_client.test_qtest_connection.return_value = True
    mock_client_class.return_value = mock_client

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "Jira API: Connected" in result.stdout
    assert "Zephyr Scale API: Connected" in result.stdout
    assert "qTest API: Connected" in result.stdout


@patch('ledzephyr.cli.load_config')
@patch('ledzephyr.cli.APIClient')
@patch('ledzephyr.cli.MetricsCalculator')
def test_metrics_command(mock_calc_class, mock_client_class, mock_load_config):
    """Test metrics command."""
    # Mock configuration
    mock_config = MagicMock()
    mock_load_config.return_value = mock_config

    # Mock client
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # Mock metrics calculator
    mock_calc = MagicMock()
    mock_metrics = ProjectMetrics(
        project_key="TEST",
        time_window="7d",
        total_tests=100,
        zephyr_tests=60,
        qtest_tests=40,
        adoption_ratio=0.4,
        coverage_parity=0.8,
        defect_link_rate=0.1,
        active_users=5
    )
    mock_calc.calculate_metrics.return_value = mock_metrics
    mock_calc_class.return_value = mock_calc

    result = runner.invoke(app, ["metrics", "-p", "TEST"])

    assert result.exit_code == 0
    assert mock_calc.calculate_metrics.call_count == 2  # Called for 7d and 30d windows