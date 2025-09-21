"""Comprehensive unit tests for CLI module to achieve 70% coverage."""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from ledzephyr.cli import app, display_json, save_csv, version_callback
from ledzephyr.models import TeamSource


@pytest.mark.unit
class TestVersionCallback:
    """Test version callback functionality."""

    def test_version_callback_true_prints_version_and_exits(self):
        """Test version callback with True prints version and exits."""
        # Arrange & Act & Assert
        with patch("ledzephyr.cli.console") as mock_console:
            with pytest.raises(typer.Exit):
                version_callback(True)
            mock_console.print.assert_called_once()
            # Should contain version string
            call_args = mock_console.print.call_args[0][0]
            assert "ledzephyr version" in call_args

    def test_version_callback_false_does_nothing(self):
        """Test version callback with False does nothing."""
        # Arrange & Act
        result = version_callback(False)

        # Assert
        assert result is None


@pytest.mark.unit
class TestMainCallback:
    """Test main callback and observability initialization."""

    def test_main_callback_initializes_observability_with_defaults(self):
        """Test main callback initializes observability with default environment."""
        # Arrange
        runner = CliRunner(mix_stderr=False)

        with (
            patch("ledzephyr.cli.init_observability") as mock_init_obs,
            patch("ledzephyr.cli.console") as mock_console,
            patch("ledzephyr.cli.load_config") as mock_config,
            patch("ledzephyr.cli.APIClient") as mock_client,
            patch("ledzephyr.cli.get_observability") as mock_obs,
            patch.dict(os.environ, {}, clear=True),
        ):
            # Mock the dependencies to avoid errors
            mock_config.return_value = Mock(zephyr_token="test", qtest_token="test")
            mock_client.return_value = Mock()
            mock_client.return_value.test_jira_connection.return_value = True
            mock_client.return_value.test_zephyr_connection.return_value = True
            mock_client.return_value.test_qtest_connection.return_value = True

            # Mock observability
            mock_obs_instance = Mock()
            mock_obs_instance.correlation_context.return_value.__enter__ = Mock()
            mock_obs_instance.correlation_context.return_value.__exit__ = Mock()
            mock_obs.return_value = mock_obs_instance

            # Act - use a real command to trigger the callback
            result = runner.invoke(app, ["doctor"])

            # Assert
            # Command should succeed
            assert result.exit_code == 0
            # Observability should be initialized
            mock_init_obs.assert_called_once_with(
                service_name="ledzephyr-cli",
                environment="development",
                otlp_endpoint=None,
                enable_tracing=False,  # development env
                enable_metrics=True,
            )

    def test_main_callback_uses_environment_variables(self):
        """Test main callback uses environment variables for configuration."""
        # Arrange
        runner = CliRunner(mix_stderr=False)

        with (
            patch("ledzephyr.cli.init_observability") as mock_init_obs,
            patch("ledzephyr.cli.console") as mock_console,
            patch("ledzephyr.cli.load_config") as mock_config,
            patch("ledzephyr.cli.APIClient") as mock_client,
            patch("ledzephyr.cli.get_observability") as mock_obs,
            patch.dict(
                os.environ,
                {"ENVIRONMENT": "production", "OTLP_ENDPOINT": "http://otel-collector:4317"},
            ),
        ):
            # Mock the dependencies to avoid errors
            mock_config.return_value = Mock(zephyr_token="test", qtest_token="test")
            mock_client.return_value = Mock()
            mock_client.return_value.test_jira_connection.return_value = True
            mock_client.return_value.test_zephyr_connection.return_value = True
            mock_client.return_value.test_qtest_connection.return_value = True

            # Mock observability
            mock_obs_instance = Mock()
            mock_obs_instance.correlation_context.return_value.__enter__ = Mock()
            mock_obs_instance.correlation_context.return_value.__exit__ = Mock()
            mock_obs.return_value = mock_obs_instance

            # Act - use a real command to trigger the callback
            result = runner.invoke(app, ["doctor"])

            # Assert
            assert result.exit_code == 0
            mock_init_obs.assert_called_once_with(
                service_name="ledzephyr-cli",
                environment="production",
                otlp_endpoint="http://otel-collector:4317",
                enable_tracing=True,  # production env
                enable_metrics=True,
            )


@pytest.mark.unit
class TestDoctorCommandComprehensive:
    """Comprehensive tests for doctor command."""

    def test_doctor_config_loading_error_shows_error_and_exits(self):
        """Test doctor command when config loading fails shows error and exits."""
        # Arrange
        runner = CliRunner(mix_stderr=False)

        with (
            patch("ledzephyr.cli.load_config") as mock_config,
            patch("ledzephyr.cli.console") as mock_console,
            patch("ledzephyr.cli.get_observability") as mock_obs,
        ):
            mock_config.side_effect = Exception("Config file not found")

            # Mock observability
            mock_obs_instance = Mock()
            mock_obs_instance.correlation_context.return_value.__enter__ = Mock()
            mock_obs_instance.correlation_context.return_value.__exit__ = Mock()
            mock_obs_instance.log = Mock()
            mock_obs.return_value = mock_obs_instance

            # Act
            result = runner.invoke(app, ["doctor"])

            # Assert
            # The error message should be printed regardless of exit code
            mock_console.print.assert_called()
            error_calls = [
                call
                for call in mock_console.print.call_args_list
                if "Error during doctor check" in str(call)
            ]
            assert len(error_calls) > 0
            # In TDD, we expect exit code 1 but will validate the implementation
            assert result.exit_code == 1

    def test_doctor_missing_zephyr_token_shows_warning(self):
        """Test doctor command with missing Zephyr token shows warning."""
        # Arrange
        runner = CliRunner(mix_stderr=False)

        with (
            patch("ledzephyr.cli.load_config") as mock_config,
            patch("ledzephyr.cli.APIClient") as mock_client_class,
            patch("ledzephyr.cli.console") as mock_console,
            patch("ledzephyr.cli.get_observability") as mock_obs,
        ):
            # Mock config without Zephyr token
            mock_config.return_value = Mock(zephyr_token=None, qtest_token="test_token")

            mock_client = Mock()
            mock_client.test_jira_connection.return_value = True
            mock_client.test_qtest_connection.return_value = True
            mock_client_class.return_value = mock_client

            # Mock observability
            mock_obs_instance = Mock()
            mock_obs_instance.correlation_context.return_value.__enter__ = Mock()
            mock_obs_instance.correlation_context.return_value.__exit__ = Mock()
            mock_obs.return_value = mock_obs_instance

            # Act
            result = runner.invoke(app, ["doctor"])

            # Assert
            assert result.exit_code == 0
            # Check that warning was printed to console
            mock_console.print.assert_called()
            warning_calls = [
                call
                for call in mock_console.print.call_args_list
                if "Zephyr Scale API: No token configured" in str(call)
            ]
            assert len(warning_calls) > 0

    def test_doctor_missing_qtest_token_shows_warning(self):
        """Test doctor command with missing qTest token shows warning."""
        # Arrange
        runner = CliRunner(mix_stderr=False)

        with (
            patch("ledzephyr.cli.load_config") as mock_config,
            patch("ledzephyr.cli.APIClient") as mock_client_class,
            patch("ledzephyr.cli.console") as mock_console,
            patch("ledzephyr.cli.get_observability") as mock_obs,
        ):
            # Mock config without qTest token
            mock_config.return_value = Mock(zephyr_token="test_token", qtest_token=None)

            mock_client = Mock()
            mock_client.test_jira_connection.return_value = True
            mock_client.test_zephyr_connection.return_value = True
            mock_client_class.return_value = mock_client

            # Mock observability
            mock_obs_instance = Mock()
            mock_obs_instance.correlation_context.return_value.__enter__ = Mock()
            mock_obs_instance.correlation_context.return_value.__exit__ = Mock()
            mock_obs.return_value = mock_obs_instance

            # Act
            result = runner.invoke(app, ["doctor"])

            # Assert
            assert result.exit_code == 0
            # Check that warning was printed to console
            mock_console.print.assert_called()
            warning_calls = [
                call
                for call in mock_console.print.call_args_list
                if "qTest API: No token configured" in str(call)
            ]
            assert len(warning_calls) > 0

    def test_doctor_api_client_creation_fails_shows_error(self):
        """Test doctor command when API client creation fails shows error."""
        # Arrange
        runner = CliRunner(mix_stderr=False)

        with (
            patch("ledzephyr.cli.load_config") as mock_config,
            patch("ledzephyr.cli.APIClient") as mock_client_class,
            patch("ledzephyr.cli.console") as mock_console,
            patch("ledzephyr.cli.get_observability") as mock_obs,
        ):
            mock_config.return_value = Mock(zephyr_token="test", qtest_token="test")
            mock_client_class.side_effect = Exception("API client creation failed")

            # Mock observability
            mock_obs_instance = Mock()
            mock_obs_instance.correlation_context.return_value.__enter__ = Mock()
            mock_obs_instance.correlation_context.return_value.__exit__ = Mock()
            mock_obs.return_value = mock_obs_instance

            # Act
            result = runner.invoke(app, ["doctor"])

            # Assert
            assert result.exit_code == 1
            # Check that error was printed to console
            mock_console.print.assert_called()
            error_calls = [
                call
                for call in mock_console.print.call_args_list
                if "Error during doctor check" in str(call)
            ]
            assert len(error_calls) > 0


@pytest.mark.unit
class TestMetricsCommandComprehensive:
    """Comprehensive tests for metrics command."""

    def test_metrics_default_windows_when_none_provided(self, sample_project_metrics):
        """Test metrics command uses default windows when none provided."""
        # Arrange
        runner = CliRunner(mix_stderr=False)
        metrics = sample_project_metrics()

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
            patch("ledzephyr.cli.console") as mock_console,
            patch("ledzephyr.cli.get_observability") as mock_obs,
        ):
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            # Mock observability
            mock_obs_instance = Mock()
            mock_obs_instance.correlation_context.return_value.__enter__ = Mock()
            mock_obs_instance.correlation_context.return_value.__exit__ = Mock()
            mock_obs_instance.log = Mock()
            mock_obs_instance.record_metric = Mock()
            mock_obs.return_value = mock_obs_instance

            # Act
            result = runner.invoke(app, ["metrics", "-p", "DEMO"])

            # Assert
            assert result.exit_code == 0
            # Should be called twice for default windows ["7d", "30d"]
            assert mock_calculator.calculate_metrics.call_count == 2

    def test_metrics_unsupported_format_shows_error(self, sample_project_metrics):
        """Test metrics command with unsupported format shows error."""
        # Arrange
        runner = CliRunner()
        metrics = sample_project_metrics()

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
        ):
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            # Act
            result = runner.invoke(app, ["metrics", "-p", "DEMO", "--format", "unsupported"])

            # Assert
            assert result.exit_code == 1
            assert "Unsupported format: unsupported" in result.stdout

    def test_metrics_excel_format_exports_file(self, sample_project_metrics, tmp_path):
        """Test metrics command with excel format exports file."""
        # Arrange
        runner = CliRunner()
        metrics = sample_project_metrics()
        output_file = tmp_path / "output.xlsx"

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
            patch("ledzephyr.cli.DataExporter") as mock_exporter_class,
        ):
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            mock_exporter = Mock()
            mock_exporter.export.return_value = output_file
            mock_exporter_class.return_value = mock_exporter

            # Act
            result = runner.invoke(
                app, ["metrics", "-p", "DEMO", "--format", "excel", "-o", str(output_file)]
            )

            # Assert
            assert result.exit_code == 0
            mock_exporter.export.assert_called_once()

    def test_metrics_pdf_format_exports_file(self, sample_project_metrics, tmp_path):
        """Test metrics command with PDF format exports file."""
        # Arrange
        runner = CliRunner()
        metrics = sample_project_metrics()
        output_file = tmp_path / "output.pdf"

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
            patch("ledzephyr.cli.DataExporter") as mock_exporter_class,
        ):
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            mock_exporter = Mock()
            mock_exporter.export.return_value = output_file
            mock_exporter_class.return_value = mock_exporter

            # Act
            result = runner.invoke(
                app, ["metrics", "-p", "DEMO", "--format", "pdf", "-o", str(output_file)]
            )

            # Assert
            assert result.exit_code == 0
            mock_exporter.export.assert_called_once()

    def test_metrics_html_format_exports_file(self, sample_project_metrics, tmp_path):
        """Test metrics command with HTML format exports file."""
        # Arrange
        runner = CliRunner()
        metrics = sample_project_metrics()
        output_file = tmp_path / "output.html"

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
            patch("ledzephyr.cli.DataExporter") as mock_exporter_class,
        ):
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            mock_exporter = Mock()
            mock_exporter.export.return_value = output_file
            mock_exporter_class.return_value = mock_exporter

            # Act
            result = runner.invoke(
                app, ["metrics", "-p", "DEMO", "--format", "html", "-o", str(output_file)]
            )

            # Assert
            assert result.exit_code == 0
            mock_exporter.export.assert_called_once()

    def test_metrics_auto_generated_filename_when_no_output(self, sample_project_metrics):
        """Test metrics command auto-generates filename when no output specified."""
        # Arrange
        runner = CliRunner()
        metrics = sample_project_metrics()

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
            patch("ledzephyr.cli.DataExporter") as mock_exporter_class,
            patch("ledzephyr.cli.datetime") as mock_datetime,
        ):
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            mock_exporter = Mock()
            mock_exporter.export.return_value = Path("metrics_DEMO_20250621_120000.csv")
            mock_exporter_class.return_value = mock_exporter

            # Mock datetime
            mock_datetime.now.return_value.strftime.return_value = "20250621_120000"

            # Act
            result = runner.invoke(app, ["metrics", "-p", "DEMO", "--format", "csv"])

            # Assert
            assert result.exit_code == 0
            mock_exporter.export.assert_called_once()

    def test_metrics_teams_source_label_option(self, sample_project_metrics):
        """Test metrics command with teams-source label option."""
        # Arrange
        runner = CliRunner()
        metrics = sample_project_metrics()

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
        ):
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            # Act
            result = runner.invoke(app, ["metrics", "-p", "DEMO", "--teams-source", "label"])

            # Assert
            assert result.exit_code == 0
            # Verify teams_source parameter was passed correctly
            mock_calculator.calculate_metrics.assert_called()
            call_args = mock_calculator.calculate_metrics.call_args[1]
            assert call_args["teams_source"] == TeamSource.LABEL

    def test_metrics_teams_source_group_option(self, sample_project_metrics):
        """Test metrics command with teams-source group option."""
        # Arrange
        runner = CliRunner()
        metrics = sample_project_metrics()

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
        ):
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            # Act
            result = runner.invoke(app, ["metrics", "-p", "DEMO", "--teams-source", "group"])

            # Assert
            assert result.exit_code == 0
            # Verify teams_source parameter was passed correctly
            mock_calculator.calculate_metrics.assert_called()
            call_args = mock_calculator.calculate_metrics.call_args[1]
            assert call_args["teams_source"] == TeamSource.GROUP

    def test_metrics_json_output_to_file(self, sample_project_metrics, tmp_path):
        """Test metrics command with JSON output to file."""
        # Arrange
        runner = CliRunner()
        metrics = sample_project_metrics()
        output_file = tmp_path / "output.json"

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
        ):
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            # Act
            result = runner.invoke(
                app, ["metrics", "-p", "DEMO", "--format", "json", "-o", str(output_file)]
            )

            # Assert
            assert result.exit_code == 0
            assert output_file.exists()

    def test_metrics_table_format_with_xlsx_output(self, sample_project_metrics, tmp_path):
        """Test metrics command with table format and xlsx output file."""
        # Arrange
        runner = CliRunner()
        metrics = sample_project_metrics()
        output_file = tmp_path / "output.xlsx"

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
            patch("ledzephyr.cli.DataExporter") as mock_exporter_class,
        ):
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            # Act
            result = runner.invoke(
                app, ["metrics", "-p", "DEMO", "--format", "table", "-o", str(output_file)]
            )

            # Assert
            assert result.exit_code == 0
            mock_exporter.export.assert_called_once_with(
                mock_calculator.calculate_metrics.return_value, output_file, format="excel"
            )

    def test_metrics_table_format_with_pdf_output(self, sample_project_metrics, tmp_path):
        """Test metrics command with table format and PDF output file."""
        # Arrange
        runner = CliRunner()
        metrics = sample_project_metrics()
        output_file = tmp_path / "output.pdf"

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
            patch("ledzephyr.cli.DataExporter") as mock_exporter_class,
        ):
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            # Act
            result = runner.invoke(
                app, ["metrics", "-p", "DEMO", "--format", "table", "-o", str(output_file)]
            )

            # Assert
            assert result.exit_code == 0
            mock_exporter.export.assert_called_once_with(
                mock_calculator.calculate_metrics.return_value, output_file, format="pdf"
            )

    def test_metrics_table_format_with_html_output(self, sample_project_metrics, tmp_path):
        """Test metrics command with table format and HTML output file."""
        # Arrange
        runner = CliRunner()
        metrics = sample_project_metrics()
        output_file = tmp_path / "output.html"

        with (
            patch("ledzephyr.cli.load_config") as _mock_config,
            patch("ledzephyr.cli.APIClient") as _mock_client,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
            patch("ledzephyr.cli.DataExporter") as mock_exporter_class,
        ):
            mock_calculator = Mock()
            mock_calculator.calculate_metrics.return_value = metrics
            mock_calc_class.return_value = mock_calculator

            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            # Act
            result = runner.invoke(
                app, ["metrics", "-p", "DEMO", "--format", "table", "-o", str(output_file)]
            )

            # Assert
            assert result.exit_code == 0
            mock_exporter.export.assert_called_once_with(
                mock_calculator.calculate_metrics.return_value, output_file, format="html"
            )

    def test_metrics_config_loading_error_shows_error(self):
        """Test metrics command when config loading fails shows error."""
        # Arrange
        runner = CliRunner()

        with patch("ledzephyr.cli.load_config") as mock_config:
            mock_config.side_effect = Exception("Config file not found")

            # Act
            result = runner.invoke(app, ["metrics", "-p", "DEMO"])

            # Assert
            assert result.exit_code == 1
            assert "Error generating metrics" in result.stdout

    def test_metrics_api_client_creation_error_shows_error(self):
        """Test metrics command when API client creation fails shows error."""
        # Arrange
        runner = CliRunner()

        with (
            patch("ledzephyr.cli.load_config") as mock_config,
            patch("ledzephyr.cli.APIClient") as mock_client_class,
        ):
            mock_config.return_value = Mock()
            mock_client_class.side_effect = Exception("API client creation failed")

            # Act
            result = runner.invoke(app, ["metrics", "-p", "DEMO"])

            # Assert
            assert result.exit_code == 1
            assert "Error generating metrics" in result.stdout

    def test_metrics_calculator_creation_error_shows_error(self):
        """Test metrics command when calculator creation fails shows error."""
        # Arrange
        runner = CliRunner()

        with (
            patch("ledzephyr.cli.load_config") as mock_config,
            patch("ledzephyr.cli.APIClient") as mock_client_class,
            patch("ledzephyr.cli.MetricsCalculator") as mock_calc_class,
        ):
            mock_config.return_value = Mock()
            mock_client_class.return_value = Mock()
            mock_calc_class.side_effect = Exception("Calculator creation failed")

            # Act
            result = runner.invoke(app, ["metrics", "-p", "DEMO"])

            # Assert
            assert result.exit_code == 1
            assert "Error generating metrics" in result.stdout


@pytest.mark.unit
class TestMonitorCommand:
    """Test monitor command functionality."""

    def test_monitor_default_params_starts_server(self):
        """Test monitor command with default parameters starts server."""
        # Arrange
        runner = CliRunner()

        with (
            patch("ledzephyr.cli.run_monitoring_server") as mock_run_server,
            # Simulate KeyboardInterrupt to exit gracefully
            patch("ledzephyr.cli.console") as mock_console,
        ):
            mock_run_server.side_effect = KeyboardInterrupt()

            # Act
            result = runner.invoke(app, ["monitor"])

            # Assert
            assert result.exit_code == 0
            mock_run_server.assert_called_once_with(host="0.0.0.0", port=8080, reload=False)

    def test_monitor_custom_host_and_port(self):
        """Test monitor command with custom host and port."""
        # Arrange
        runner = CliRunner()

        with (
            patch("ledzephyr.cli.run_monitoring_server") as mock_run_server,
            patch("ledzephyr.cli.console") as mock_console,
        ):
            mock_run_server.side_effect = KeyboardInterrupt()

            # Act
            result = runner.invoke(app, ["monitor", "--host", "127.0.0.1", "--port", "9090"])

            # Assert
            assert result.exit_code == 0
            mock_run_server.assert_called_once_with(host="127.0.0.1", port=9090, reload=False)

    def test_monitor_server_error_shows_error_and_exits(self):
        """Test monitor command when server error occurs shows error and exits."""
        # Arrange
        runner = CliRunner()

        with (
            patch("ledzephyr.cli.run_monitoring_server") as mock_run_server,
            patch("ledzephyr.cli.console") as mock_console,
        ):
            mock_run_server.side_effect = Exception("Server startup failed")

            # Act
            result = runner.invoke(app, ["monitor"])

            # Assert
            assert result.exit_code == 1
            # Check that error message was printed
            mock_console.print.assert_called()
            error_calls = [
                call
                for call in mock_console.print.call_args_list
                if "Error running monitoring server" in str(call)
            ]
            assert len(error_calls) > 0

    def test_monitor_import_error_shows_error_and_exits(self):
        """Test monitor command when import fails shows error and exits."""
        # Arrange
        runner = CliRunner()

        with (
            # Mock the import to fail
            patch(
                "ledzephyr.cli.run_monitoring_server", side_effect=ImportError("Module not found")
            ),
            patch("ledzephyr.cli.console") as mock_console,
        ):
            # Act
            result = runner.invoke(app, ["monitor"])

            # Assert
            assert result.exit_code == 1


@pytest.mark.unit
class TestHelperFunctions:
    """Test CLI helper functions."""

    def test_display_json_without_output_prints_json(self, sample_project_metrics):
        """Test display_json without output file prints JSON to console."""
        # Arrange
        metrics_data = {"7d": sample_project_metrics()}

        with patch("ledzephyr.cli.console") as mock_console:
            # Act
            display_json(metrics_data, None)

            # Assert
            mock_console.print.assert_called_once()
            # Check that the printed content is valid JSON
            printed_content = mock_console.print.call_args[0][0]
            parsed_json = json.loads(printed_content)
            assert "7d" in parsed_json

    def test_display_json_with_output_writes_file(self, sample_project_metrics, tmp_path):
        """Test display_json with output file writes JSON to file."""
        # Arrange
        metrics_data = {"7d": sample_project_metrics()}
        output_file = tmp_path / "output.json"

        # Act
        display_json(metrics_data, output_file)

        # Assert
        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
        assert "7d" in data
        assert data["7d"]["project_key"] == "DEMO"

    def test_save_csv_creates_valid_csv_file(self, sample_project_metrics, tmp_path):
        """Test save_csv creates valid CSV file with correct headers and data."""
        # Arrange
        metrics = sample_project_metrics()
        metrics_data = {"7d": metrics, "30d": metrics}
        csv_file = tmp_path / "output.csv"

        # Act
        save_csv(metrics_data, csv_file)

        # Assert
        assert csv_file.exists()
        content = csv_file.read_text()

        # Check headers
        assert "window,total_tests,zephyr_tests,qtest_tests" in content
        assert "adoption_ratio,active_users,coverage_parity,defect_link_rate" in content

        # Check data rows
        assert "7d,150" in content
        assert "30d,150" in content

    def test_save_csv_handles_special_characters_in_data(self, tmp_path):
        """Test save_csv handles special characters in data correctly."""
        # Arrange
        from ledzephyr.models import ProjectMetrics

        # Create metrics with special characters
        metrics = ProjectMetrics(
            project_key="TEST,WITH,COMMAS",
            time_window="7d",
            total_tests=100,
            zephyr_tests=50,
            qtest_tests=50,
            adoption_ratio=0.5,
            active_users=10,
            coverage_parity=0.8,
            defect_link_rate=0.2,
        )
        metrics_data = {"7d": metrics}
        csv_file = tmp_path / "output.csv"

        # Act
        save_csv(metrics_data, csv_file)

        # Assert
        assert csv_file.exists()
        content = csv_file.read_text()
        # CSV should properly handle the commas in project key
        assert "7d,100" in content


@pytest.mark.unit
class TestInvalidArguments:
    """Test CLI with invalid argument scenarios."""

    def test_invalid_teams_source_shows_error(self):
        """Test metrics command with invalid teams source shows error."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(app, ["metrics", "-p", "DEMO", "--teams-source", "invalid"])

        # Assert
        assert result.exit_code != 0
        assert "Invalid value" in result.stdout or "invalid choice" in result.stdout

    def test_invalid_command_shows_error(self):
        """Test CLI with invalid command shows error."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(app, ["invalid-command"])

        # Assert
        assert result.exit_code != 0
        assert "No such command" in result.stdout or "invalid" in result.stdout.lower()

    def test_metrics_negative_port_in_monitor_shows_error(self):
        """Test monitor command with negative port shows error."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(app, ["monitor", "--port", "-1"])

        # Assert
        assert result.exit_code != 0

    def test_metrics_invalid_port_in_monitor_shows_error(self):
        """Test monitor command with invalid port shows error."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(app, ["monitor", "--port", "invalid"])

        # Assert
        assert result.exit_code != 0

    def test_help_flag_shows_help(self):
        """Test --help flag shows help message."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(app, ["--help"])

        # Assert
        assert result.exit_code == 0
        assert "CLI tool to report Zephyr Scale" in result.stdout
        assert "doctor" in result.stdout
        assert "metrics" in result.stdout
        assert "monitor" in result.stdout

    def test_command_help_shows_command_help(self):
        """Test command --help shows command-specific help."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(app, ["metrics", "--help"])

        # Assert
        assert result.exit_code == 0
        assert "Generate migration metrics" in result.stdout
        assert "--project" in result.stdout
        assert "--window" in result.stdout

    def test_version_flag_shows_version(self):
        """Test --version flag shows version and exits."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(app, ["--version"])

        # Assert
        assert result.exit_code == 0
        output = result.stdout or str(result.output)
        assert "ledzephyr version" in output

    def test_no_args_shows_help(self):
        """Test CLI with no arguments shows help."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(app, [])

        # Assert
        assert result.exit_code == 0
        assert "Usage:" in result.stdout or "CLI tool to report" in result.stdout
