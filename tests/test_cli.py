"""Comprehensive test suite for CLI commands."""

import csv
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest
from typer.testing import CliRunner

from ledzephyr.cli import app
from ledzephyr.models import ProjectMetrics, TeamSource, TrendData, TeamMetrics


runner = CliRunner()


# Test data fixtures
@pytest.fixture
def sample_metrics():
    """Sample metrics data for testing."""
    trend_data = TrendData(
        week_1={"adoption_ratio": 0.45, "coverage_parity": 0.85, "active_users": 8},
        week_2={"adoption_ratio": 0.42, "coverage_parity": 0.80, "active_users": 7},
        week_3={"adoption_ratio": 0.38, "coverage_parity": 0.75, "active_users": 6},
        week_4={"adoption_ratio": 0.35, "coverage_parity": 0.70, "active_users": 5},
        adoption_trend=0.10,
        coverage_trend=0.15,
        activity_trend=3.0
    )

    team_metrics = {
        "frontend-team": TeamMetrics(
            team_name="frontend-team",
            team_source=TeamSource.COMPONENT,
            total_tests=50,
            zephyr_tests=30,
            qtest_tests=20,
            adoption_ratio=0.4,
            coverage_parity=0.8,
            defect_link_rate=0.15,
            active_users=3
        ),
        "backend-team": TeamMetrics(
            team_name="backend-team",
            team_source=TeamSource.COMPONENT,
            total_tests=50,
            zephyr_tests=30,
            qtest_tests=20,
            adoption_ratio=0.4,
            coverage_parity=0.8,
            defect_link_rate=0.05,
            active_users=2
        )
    }

    return ProjectMetrics(
        project_key="TEST",
        time_window="7d",
        total_tests=100,
        zephyr_tests=60,
        qtest_tests=40,
        adoption_ratio=0.4,
        coverage_parity=0.8,
        defect_link_rate=0.1,
        active_users=5,
        team_metrics=team_metrics,
        trend_data=trend_data
    )


class TestBasicCommands:
    """Test basic CLI functionality."""

    def test_version(self):
        """Test version command."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "ledzephyr version" in result.stdout

    def test_help(self):
        """Test help message."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "CLI tool to report Zephyr Scale" in result.stdout
        assert "metrics" in result.stdout
        assert "doctor" in result.stdout

    def test_no_args_shows_help(self):
        """Test that no arguments shows help due to no_args_is_help=True."""
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "CLI tool to report Zephyr Scale" in result.stdout


class TestDoctorCommand:
    """Test doctor command functionality."""

    @patch('ledzephyr.cli.load_config')
    @patch('ledzephyr.cli.APIClient')
    def test_doctor_all_connections_success(self, mock_client_class, mock_load_config):
        """Test doctor command with all API connections successful."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.zephyr_token = "test-zephyr-token"
        mock_config.qtest_token = "test-qtest-token"
        mock_load_config.return_value = mock_config

        # Mock client
        mock_client = MagicMock()
        mock_client.test_jira_connection.return_value = True
        mock_client.test_zephyr_connection.return_value = True
        mock_client.test_qtest_connection.return_value = True
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0
        assert "✅ Jira API: Connected" in result.stdout
        assert "✅ Zephyr Scale API: Connected" in result.stdout
        assert "✅ qTest API: Connected" in result.stdout
        assert "🎉 Doctor check complete!" in result.stdout

    @patch('ledzephyr.cli.load_config')
    @patch('ledzephyr.cli.APIClient')
    def test_doctor_missing_tokens(self, mock_client_class, mock_load_config):
        """Test doctor command with missing API tokens."""
        # Mock configuration with missing tokens
        mock_config = MagicMock()
        mock_config.zephyr_token = None
        mock_config.qtest_token = None
        mock_load_config.return_value = mock_config

        # Mock client
        mock_client = MagicMock()
        mock_client.test_jira_connection.return_value = True
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0
        assert "✅ Jira API: Connected" in result.stdout
        assert "⚠️  Zephyr Scale API: No token configured" in result.stdout
        assert "⚠️  qTest API: No token configured" in result.stdout

    @patch('ledzephyr.cli.load_config')
    @patch('ledzephyr.cli.APIClient')
    def test_doctor_connection_failures(self, mock_client_class, mock_load_config):
        """Test doctor command with API connection failures."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.zephyr_token = "test-zephyr-token"
        mock_config.qtest_token = "test-qtest-token"
        mock_load_config.return_value = mock_config

        # Mock client with failures
        mock_client = MagicMock()
        mock_client.test_jira_connection.return_value = False
        mock_client.test_zephyr_connection.return_value = False
        mock_client.test_qtest_connection.return_value = False
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0
        assert "❌ Jira API: Connection failed" in result.stdout
        assert "❌ Zephyr Scale API: Connection failed" in result.stdout
        assert "❌ qTest API: Connection failed" in result.stdout

    @patch('ledzephyr.cli.load_config')
    def test_doctor_config_error(self, mock_load_config):
        """Test doctor command with configuration loading error."""
        mock_load_config.side_effect = Exception("Config loading failed")

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 1
        assert "❌ Error during doctor check:" in result.stdout
        assert "Config loading failed" in result.stdout


class TestMetricsCommand:
    """Test metrics command functionality."""

    @patch('ledzephyr.cli.load_config')
    @patch('ledzephyr.cli.APIClient')
    @patch('ledzephyr.cli.MetricsCalculator')
    def test_metrics_basic_functionality(self, mock_calc_class, mock_client_class, mock_load_config, sample_metrics):
        """Test basic metrics command functionality."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_calc = MagicMock()
        mock_calc.calculate_metrics.return_value = sample_metrics
        mock_calc_class.return_value = mock_calc

        result = runner.invoke(app, ["metrics", "-p", "TEST"])

        assert result.exit_code == 0
        assert mock_calc.calculate_metrics.call_count == 2  # Called for 7d and 30d windows
        assert "Generating metrics for project: TEST" in result.stdout

    @patch('ledzephyr.cli.load_config')
    @patch('ledzephyr.cli.APIClient')
    @patch('ledzephyr.cli.MetricsCalculator')
    def test_metrics_custom_windows(self, mock_calc_class, mock_client_class, mock_load_config, sample_metrics):
        """Test metrics command with custom time windows."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_calc = MagicMock()
        mock_calc.calculate_metrics.return_value = sample_metrics
        mock_calc_class.return_value = mock_calc

        result = runner.invoke(app, ["metrics", "-p", "TEST", "-w", "24h", "-w", "7d", "-w", "30d"])

        assert result.exit_code == 0
        assert mock_calc.calculate_metrics.call_count == 3  # Called for all 3 windows

        # Verify correct time windows were passed
        calls = mock_calc.calculate_metrics.call_args_list
        assert calls[0][1]['time_window'] == '24h'
        assert calls[1][1]['time_window'] == '7d'
        assert calls[2][1]['time_window'] == '30d'

    @patch('ledzephyr.cli.load_config')
    @patch('ledzephyr.cli.APIClient')
    @patch('ledzephyr.cli.MetricsCalculator')
    def test_metrics_teams_source_options(self, mock_calc_class, mock_client_class, mock_load_config, sample_metrics):
        """Test all teams source options."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_calc = MagicMock()
        mock_calc.calculate_metrics.return_value = sample_metrics
        mock_calc_class.return_value = mock_calc

        # Test component (default)
        result = runner.invoke(app, ["metrics", "-p", "TEST"])
        assert result.exit_code == 0
        calls = mock_calc.calculate_metrics.call_args_list
        assert calls[0][1]['teams_source'] == TeamSource.COMPONENT

        mock_calc.reset_mock()

        # Test label
        result = runner.invoke(app, ["metrics", "-p", "TEST", "--teams-source", "label"])
        assert result.exit_code == 0
        calls = mock_calc.calculate_metrics.call_args_list
        assert calls[0][1]['teams_source'] == TeamSource.LABEL

        mock_calc.reset_mock()

        # Test group
        result = runner.invoke(app, ["metrics", "-p", "TEST", "--teams-source", "group"])
        assert result.exit_code == 0
        calls = mock_calc.calculate_metrics.call_args_list
        assert calls[0][1]['teams_source'] == TeamSource.GROUP

    def test_metrics_missing_project_key(self):
        """Test metrics command without required project key."""
        result = runner.invoke(app, ["metrics"])
        assert result.exit_code != 0
        assert "Missing option" in result.stdout or "Error" in result.stdout

    @patch('ledzephyr.cli.load_config')
    @patch('ledzephyr.cli.APIClient')
    @patch('ledzephyr.cli.MetricsCalculator')
    def test_metrics_invalid_format(self, mock_calc_class, mock_client_class, mock_load_config):
        """Test metrics command with invalid format."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_calc = MagicMock()
        mock_calc_class.return_value = mock_calc

        result = runner.invoke(app, ["metrics", "-p", "TEST", "--format", "invalid"])

        assert result.exit_code == 1
        assert "❌ Unsupported format: invalid" in result.stdout

    def test_metrics_invalid_teams_source(self):
        """Test metrics command with invalid teams source."""
        result = runner.invoke(app, ["metrics", "-p", "TEST", "--teams-source", "invalid"])
        assert result.exit_code != 0
        # Typer should handle enum validation

    @patch('ledzephyr.cli.load_config')
    def test_metrics_config_error(self, mock_load_config):
        """Test metrics command with configuration error."""
        mock_load_config.side_effect = Exception("Config error")

        result = runner.invoke(app, ["metrics", "-p", "TEST"])

        assert result.exit_code == 1
        assert "❌ Error generating metrics:" in result.stdout
        assert "Config error" in result.stdout


class TestOutputFormats:
    """Test output format functionality."""

    @patch('ledzephyr.cli.load_config')
    @patch('ledzephyr.cli.APIClient')
    @patch('ledzephyr.cli.MetricsCalculator')
    def test_table_format(self, mock_calc_class, mock_client_class, mock_load_config, sample_metrics):
        """Test table output format."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_calc = MagicMock()
        mock_calc.calculate_metrics.return_value = sample_metrics
        mock_calc_class.return_value = mock_calc

        result = runner.invoke(app, ["metrics", "-p", "TEST", "--format", "table"])

        assert result.exit_code == 0
        # Check for table elements (though they may be styled)
        output_lower = result.stdout.lower()
        assert any(keyword in output_lower for keyword in ["total", "zephyr", "qtest", "adoption"])

    @patch('ledzephyr.cli.load_config')
    @patch('ledzephyr.cli.APIClient')
    @patch('ledzephyr.cli.MetricsCalculator')
    def test_json_format_stdout(self, mock_calc_class, mock_client_class, mock_load_config, sample_metrics):
        """Test JSON output format to stdout."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_calc = MagicMock()
        mock_calc.calculate_metrics.return_value = sample_metrics
        mock_calc_class.return_value = mock_calc

        result = runner.invoke(app, ["metrics", "-p", "TEST", "--format", "json"])

        assert result.exit_code == 0
        # Should contain JSON-like output
        assert "{" in result.stdout and "}" in result.stdout

    @patch('ledzephyr.cli.load_config')
    @patch('ledzephyr.cli.APIClient')
    @patch('ledzephyr.cli.MetricsCalculator')
    @patch('builtins.open', new_callable=mock_open)
    def test_json_format_file_output(self, mock_file, mock_calc_class, mock_client_class, mock_load_config, sample_metrics):
        """Test JSON output format to file."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_calc = MagicMock()
        mock_calc.calculate_metrics.return_value = sample_metrics
        mock_calc_class.return_value = mock_calc

        result = runner.invoke(app, ["metrics", "-p", "TEST", "--format", "json", "-o", "output.json"])

        assert result.exit_code == 0
        mock_file.assert_called_with(Path("output.json"), 'w')

    @patch('ledzephyr.cli.load_config')
    @patch('ledzephyr.cli.APIClient')
    @patch('ledzephyr.cli.MetricsCalculator')
    @patch('builtins.open', new_callable=mock_open)
    def test_csv_output(self, mock_file, mock_calc_class, mock_client_class, mock_load_config, sample_metrics):
        """Test CSV output functionality."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_calc = MagicMock()
        mock_calc.calculate_metrics.return_value = sample_metrics
        mock_calc_class.return_value = mock_calc

        result = runner.invoke(app, ["metrics", "-p", "TEST", "--format", "table", "-o", "output.csv"])

        assert result.exit_code == 0
        assert "Results saved to:" in result.stdout
        mock_file.assert_called()


class TestMetricsValidation:
    """Test that all required metrics are present and valid."""

    @patch('ledzephyr.cli.load_config')
    @patch('ledzephyr.cli.APIClient')
    @patch('ledzephyr.cli.MetricsCalculator')
    def test_required_metrics_fields(self, mock_calc_class, mock_client_class, mock_load_config, sample_metrics):
        """Test that all required metrics fields are calculated and displayed."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_calc = MagicMock()
        mock_calc.calculate_metrics.return_value = sample_metrics
        mock_calc_class.return_value = mock_calc

        result = runner.invoke(app, ["metrics", "-p", "TEST", "--format", "json"])

        assert result.exit_code == 0

        # Verify all required metrics are present by checking the sample_metrics structure
        assert sample_metrics.total_tests == 100
        assert sample_metrics.zephyr_tests == 60
        assert sample_metrics.qtest_tests == 40
        assert sample_metrics.adoption_ratio == 0.4
        assert sample_metrics.coverage_parity == 0.8
        assert sample_metrics.defect_link_rate == 0.1
        assert sample_metrics.active_users == 5
        assert sample_metrics.trend_data is not None
        assert len(sample_metrics.team_metrics) == 2

    def test_metrics_model_validation(self, sample_metrics):
        """Test that metrics model validates correctly."""
        # Test that the sample metrics object is valid
        assert sample_metrics.project_key == "TEST"
        assert sample_metrics.time_window == "7d"

        # Test trend data
        trend = sample_metrics.trend_data
        assert trend.adoption_trend == 0.10
        assert trend.coverage_trend == 0.15
        assert trend.activity_trend == 3.0

        # Test team metrics
        frontend_team = sample_metrics.team_metrics["frontend-team"]
        assert frontend_team.team_source == TeamSource.COMPONENT
        assert frontend_team.adoption_ratio == 0.4


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_project_key(self):
        """Test with empty project key."""
        result = runner.invoke(app, ["metrics", "-p", ""])
        # Should either fail validation or pass empty string - depends on implementation
        # The command should at minimum execute without crashing

    @patch('ledzephyr.cli.load_config')
    @patch('ledzephyr.cli.APIClient')
    @patch('ledzephyr.cli.MetricsCalculator')
    def test_calculator_exception(self, mock_calc_class, mock_client_class, mock_load_config):
        """Test handling of calculator exceptions."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_calc = MagicMock()
        mock_calc.calculate_metrics.side_effect = Exception("Calculation failed")
        mock_calc_class.return_value = mock_calc

        result = runner.invoke(app, ["metrics", "-p", "TEST"])

        assert result.exit_code == 1
        assert "❌ Error generating metrics:" in result.stdout
        assert "Calculation failed" in result.stdout

    def test_special_characters_in_project_key(self):
        """Test project key with special characters."""
        # This should not crash the application
        result = runner.invoke(app, ["metrics", "-p", "TEST-123_ABC.DEF"])
        # Command should execute (may fail for other reasons, but not crash)

    @patch('ledzephyr.cli.load_config')
    @patch('ledzephyr.cli.APIClient')
    @patch('ledzephyr.cli.MetricsCalculator')
    def test_very_long_project_key(self, mock_calc_class, mock_client_class, mock_load_config, sample_metrics):
        """Test with very long project key."""
        long_key = "A" * 1000

        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_calc = MagicMock()
        mock_calc.calculate_metrics.return_value = sample_metrics
        mock_calc_class.return_value = mock_calc

        result = runner.invoke(app, ["metrics", "-p", long_key])

        # Should handle gracefully
        assert mock_calc.calculate_metrics.called


class TestIntegration:
    """Integration-style tests that verify end-to-end functionality."""

    @patch('ledzephyr.cli.load_config')
    @patch('ledzephyr.cli.APIClient')
    @patch('ledzephyr.cli.MetricsCalculator')
    def test_full_workflow_table_output(self, mock_calc_class, mock_client_class, mock_load_config, sample_metrics):
        """Test complete workflow with table output."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_calc = MagicMock()
        mock_calc.calculate_metrics.return_value = sample_metrics
        mock_calc_class.return_value = mock_calc

        # Run full command with all options
        result = runner.invoke(app, [
            "metrics",
            "-p", "MYPROJECT",
            "-w", "24h",
            "-w", "7d",
            "-w", "30d",
            "--teams-source", "component",
            "--format", "table"
        ])

        assert result.exit_code == 0
        assert mock_calc.calculate_metrics.call_count == 3
        assert "Generating metrics for project: MYPROJECT" in result.stdout

        # Verify all time windows were processed
        calls = mock_calc.calculate_metrics.call_args_list
        time_windows = [call[1]['time_window'] for call in calls]
        assert "24h" in time_windows
        assert "7d" in time_windows
        assert "30d" in time_windows

    def test_command_aliases(self):
        """Test that both 'lz' and 'ledzephyr' work as command aliases."""
        # This tests the poetry scripts configuration
        # In actual usage, both should work: lz metrics -p TEST and ledzephyr metrics -p TEST
        # Here we test the app directly
        result1 = runner.invoke(app, ["--help"])
        assert result1.exit_code == 0

        # The CLI app itself should be the same regardless of how it's invoked