"""Integration tests for CLI with external dependencies."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ledzephyr.cli import app


@pytest.mark.integration
class TestCLIIntegration:
    """Integration tests for CLI commands with mocked external services."""

    @pytest.mark.enable_socket
    def test_doctor_command_integration_mocked_services_full_workflow(self, mock_responses):
        """Test doctor command integration with mocked services runs full workflow."""
        # Arrange
        runner = CliRunner()

        # Mock HTTP responses for all services
        mock_responses.add("https://example.atlassian.net/rest/api/2/myself", {
            "self": "https://example.atlassian.net/rest/api/2/user?accountId=123",
            "accountId": "123",
            "displayName": "Test User"
        })

        mock_responses.add("https://example.atlassian.net/rest/zephyr/latest/util/versionInfo", {
            "version": "1.0"
        })

        mock_responses.add("https://example.qtestnet.com/api/v3/projects", [
            {"id": 1, "name": "Test Project"}
        ])

        with patch.dict('os.environ', {
            'LEDZEPHYR_JIRA_URL': 'https://example.atlassian.net',
            'LEDZEPHYR_JIRA_USERNAME': 'test@example.com',
            'LEDZEPHYR_JIRA_API_TOKEN': 'fake_token',
            'LEDZEPHYR_ZEPHYR_URL': 'https://example.atlassian.net',
            'LEDZEPHYR_ZEPHYR_TOKEN': 'fake_token',
            'LEDZEPHYR_QTEST_URL': 'https://example.qtestnet.com',
            'LEDZEPHYR_QTEST_TOKEN': 'fake_token'
        }):
            # Act
            result = runner.invoke(app, ["doctor"])

        # Assert
        assert result.exit_code == 0
        assert "ledzephyr doctor" in result.stdout
        assert "Doctor check complete!" in result.stdout

    def test_metrics_command_integration_mocked_apis_returns_metrics(self, tmp_path):
        """Test metrics command integration with mocked APIs returns metrics."""
        # Arrange
        runner = CliRunner()
        output_file = tmp_path / "test_metrics.json"

        # Mock the metrics calculation to return test data
        with patch('ledzephyr.cli.get_project_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "7d": {
                    "project_key": "DEMO",
                    "time_window": "7d",
                    "total_tests": 150,
                    "qtest_tests": 60,
                    "zephyr_tests": 90,
                    "adoption_ratio": 0.4,
                    "active_users": 8,
                    "coverage_parity": 0.85,
                    "defect_link_rate": 0.12
                }
            }

            with patch.dict('os.environ', {
                'LEDZEPHYR_JIRA_URL': 'https://example.atlassian.net',
                'LEDZEPHYR_JIRA_USERNAME': 'test@example.com',
                'LEDZEPHYR_JIRA_API_TOKEN': 'fake_token',
                'LEDZEPHYR_ZEPHYR_URL': 'https://example.atlassian.net',
                'LEDZEPHYR_ZEPHYR_TOKEN': 'fake_token',
                'LEDZEPHYR_QTEST_URL': 'https://example.qtestnet.com',
                'LEDZEPHYR_QTEST_TOKEN': 'fake_token'
            }):
                # Act
                result = runner.invoke(app, [
                    "metrics", "-p", "DEMO",
                    "--format", "json",
                    "--out", str(output_file)
                ])

        # Assert
        assert result.exit_code == 0
        assert output_file.exists()

        output_data = json.loads(output_file.read_text())
        assert "7d" in output_data
        assert output_data["7d"]["project_key"] == "DEMO"
        assert output_data["7d"]["total_tests"] == 150

    def test_end_to_end_workflow_config_to_output_complete_flow(self, tmp_path):
        """Test end-to-end workflow from config to output runs complete flow."""
        # Arrange
        runner = CliRunner()
        env_file = tmp_path / ".env"
        output_file = tmp_path / "e2e_metrics.csv"

        # Create test environment file
        env_file.write_text(
            "LEDZEPHYR_JIRA_URL=https://e2e.atlassian.net\n"
            "LEDZEPHYR_JIRA_USERNAME=e2e@example.com\n"
            "LEDZEPHYR_JIRA_API_TOKEN=e2e_token\n"
            "LEDZEPHYR_ZEPHYR_URL=https://e2e.atlassian.net\n"
            "LEDZEPHYR_ZEPHYR_TOKEN=e2e_token\n"
            "LEDZEPHYR_QTEST_URL=https://e2e.qtestnet.com\n"
            "LEDZEPHYR_QTEST_TOKEN=e2e_token\n"
        )

        # Mock the complete metrics pipeline
        with patch('ledzephyr.cli.load_config') as mock_config, \
             patch('ledzephyr.cli.get_project_metrics') as mock_metrics:

            mock_config.return_value = type('Config', (), {
                'jira_url': 'https://e2e.atlassian.net',
                'jira_username': 'e2e@example.com',
                'jira_token': 'e2e_token',
                'timeout': 30,
                'max_retries': 3
            })()

            mock_metrics.return_value = {
                "24h": {
                    "project_key": "E2E",
                    "time_window": "24h",
                    "total_tests": 100,
                    "qtest_tests": 40,
                    "zephyr_tests": 60,
                    "adoption_ratio": 0.4,
                    "active_users": 5,
                    "coverage_parity": 0.8,
                    "defect_link_rate": 0.15
                },
                "7d": {
                    "project_key": "E2E",
                    "time_window": "7d",
                    "total_tests": 500,
                    "qtest_tests": 200,
                    "zephyr_tests": 300,
                    "adoption_ratio": 0.4,
                    "active_users": 15,
                    "coverage_parity": 0.85,
                    "defect_link_rate": 0.2
                }
            }

            # Act - Run complete workflow
            result = runner.invoke(app, [
                "metrics", "-p", "E2E",
                "-w", "24h", "-w", "7d",
                "--teams-source", "component",
                "--format", "table",
                "--out", str(output_file)
            ])

        # Assert
        assert result.exit_code == 0
        assert output_file.exists()

        csv_content = output_file.read_text()
        assert "window,total_tests" in csv_content
        assert "24h,100" in csv_content
        assert "7d,500" in csv_content