"""Unit tests for CLI module following AAA pattern."""

import json
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from ledzephyr.cli import app


@pytest.mark.unit
class TestDoctorCommand:
    """Test doctor command."""

    def test_doctor_all_connections_succeed_shows_success(self, requests_mock):
        """Test doctor command when all connections succeed shows success."""
        # Arrange
        runner = CliRunner()

        with (
            patch("ledzephyr.cli.load_config") as mock_config,
            patch("ledzephyr.cli.APIClient") as mock_client_class,
        ):
            # Mock config
            mock_config.return_value = Mock(zephyr_token="test_token", qtest_token="test_token")

            # Mock client methods
            mock_client = Mock()
            mock_client.test_jira_connection.return_value = True
            mock_client.test_zephyr_connection.return_value = True
            mock_client.test_qtest_connection.return_value = True
            mock_client_class.return_value = mock_client

            # Act
            result = runner.invoke(app, ["doctor"])

            # Assert
            assert result.exit_code == 0
            assert "Jira API: Connected" in result.stdout
            assert "Doctor check complete!" in result.stdout

    def test_doctor_connection_fails_shows_failure(self, requests_mock):
        """Test doctor command when connection fails shows failure."""
        # Arrange
        runner = CliRunner()

        with (
            patch("ledzephyr.cli.load_config") as mock_config,
            patch("ledzephyr.cli.APIClient") as mock_client_class,
        ):
            # Mock config
            mock_config.return_value = Mock(zephyr_token="test_token", qtest_token="test_token")

            # Mock client methods - Jira fails, others succeed
            mock_client = Mock()
            mock_client.test_jira_connection.return_value = False
            mock_client.test_zephyr_connection.return_value = True
            mock_client.test_qtest_connection.return_value = True
            mock_client_class.return_value = mock_client

            # Act
            result = runner.invoke(app, ["doctor"])

            # Assert
            assert result.exit_code == 0
            assert "Jira API: Connection failed" in result.stdout


@pytest.mark.unit
class TestMetricsCommand:
    """Test metrics command."""

    def test_metrics_basic_invocation_valid_project_returns_table(self, sample_project_metrics):
        """Test metrics command basic invocation with valid project returns table."""
        # Arrange
        runner = CliRunner()
        metrics = sample_project_metrics()

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
        ):
            # Mock calculator
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            # Act
            result = runner.invoke(app, ["metrics", "-p", "DEMO", "-w", "7d", "-w", "30d"])

            # Assert
            assert result.exit_code == 0
            assert "Migration Metrics" in result.stdout
            assert "DEMO" in result.stdout

    def test_metrics_json_format_valid_project_returns_json(self, sample_project_metrics):
        """Test metrics command with JSON format returns valid JSON."""
        # Arrange
        runner = CliRunner()
        metrics = sample_project_metrics()

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
        ):
            # Mock calculator
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            # Act
            result = runner.invoke(
                app, ["metrics", "-p", "DEMO", "--format", "json", "-w", "7d", "-w", "30d"]
            )

            # Assert
            assert result.exit_code == 0
            # Extract JSON from output (skip progress messages)
            json_start = result.stdout.find("{")
            json_output = result.stdout[json_start:]
            output_data = json.loads(json_output)
            assert "7d" in output_data
            assert output_data["7d"]["project_key"] == "DEMO"

    def test_metrics_custom_time_windows_multiple_windows_returns_data(
        self, sample_project_metrics
    ):
        """Test metrics command with custom time windows returns data for all windows."""
        # Arrange
        runner = CliRunner()
        metrics = sample_project_metrics()

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
        ):
            # Mock calculator
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            # Act
            result = runner.invoke(
                app, ["metrics", "-p", "DEMO", "-w", "24h", "-w", "7d", "-w", "30d"]
            )

            # Assert
            assert result.exit_code == 0
            assert "24h" in result.stdout
            assert "7d" in result.stdout
            assert "30d" in result.stdout

    def test_metrics_csv_output_valid_data_creates_csv(self, sample_project_metrics, tmp_path):
        """Test metrics command with CSV output creates valid CSV file."""
        # Arrange
        runner = CliRunner()
        metrics = sample_project_metrics()
        csv_file = tmp_path / "sample_output.csv"

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
        ):
            # Mock calculator
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            # Act
            result = runner.invoke(
                app,
                [
                    "metrics",
                    "-p",
                    "DEMO",
                    "--format",
                    "table",
                    "--out",
                    str(csv_file),
                    "-w",
                    "7d",
                    "-w",
                    "30d",
                ],
            )

            # Assert
            assert result.exit_code == 0
            assert csv_file.exists()
            csv_content = csv_file.read_text()
            assert "window,total_tests" in csv_content
            assert "7d,150" in csv_content

    def test_metrics_teams_source_component_valid_source_returns_data(self, sample_project_metrics):
        """Test metrics command with teams-source component returns data."""
        # Arrange
        runner = CliRunner()
        metrics = sample_project_metrics()

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
        ):
            # Mock calculator
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            # Act
            result = runner.invoke(
                app,
                ["metrics", "-p", "DEMO", "--teams-source", "component", "-w", "7d", "-w", "30d"],
            )

            # Assert
            assert result.exit_code == 0
            assert "Migration Metrics" in result.stdout

    def test_metrics_invalid_project_key_missing_project_shows_error(self):
        """Test metrics command with missing project key shows error."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(app, ["metrics"])

        # Assert
        assert result.exit_code != 0
        assert "Missing option" in result.stdout or "required" in result.stdout

    def test_metrics_api_error_service_unavailable_shows_error(self, sample_project_metrics):
        """Test metrics command when API error occurs shows error."""
        # Arrange
        runner = CliRunner()

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
        ):
            # Mock calculator to raise exception
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.side_effect = Exception("API service unavailable")
            mock_calc_class.return_value = mock_calculator

            # Act
            result = runner.invoke(app, ["metrics", "-p", "DEMO", "-w", "7d", "-w", "30d"])

            # Assert
            assert result.exit_code != 0
            assert "Error" in result.stdout or "failed" in result.stdout


@pytest.mark.unit
class TestHelperFunctions:
    """Test CLI helper functions."""

    def test_display_table_valid_metrics_displays_table(self, sample_project_metrics):
        """Test display_table with valid metrics displays table."""
        # Arrange
        metrics_data = {"7d": sample_project_metrics()}

        with patch("ledzephyr.cli.console") as mock_console:
            # Act
            from ledzephyr.cli import display_table

            display_table(metrics_data)

            # Assert
            mock_console.print.assert_called()

    def test_save_csv_valid_metrics_creates_file(self, sample_project_metrics, tmp_path):
        """Test save_csv with valid metrics creates CSV file."""
        # Arrange
        metrics = sample_project_metrics()
        metrics_data = {"7d": metrics}
        csv_file = tmp_path / "sample.csv"

        # Act
        from ledzephyr.cli import save_csv

        save_csv(metrics_data, csv_file)

        # Assert
        assert csv_file.exists()
        content = csv_file.read_text()
        assert "window,total_tests" in content
