"""Unit tests for configuration module following AAA pattern."""

import pytest
from pydantic import ValidationError

from ledzephyr.config import Config, load_config


@pytest.mark.unit
@pytest.mark.auth
class TestConfig:
    """Test Config domain model."""

    def test_create_config_valid_data_creates_instance(self, mock_config):
        """Test creating Config with valid data creates instance."""
        # Arrange
        config_data = mock_config()

        # Act
        config = Config(**config_data)

        # Assert
        assert config.jira_url == "https://example.atlassian.net"
        assert config.jira_username == "demo@example.com"
        assert config.timeout == 30

    def test_jira_url_validation_valid_url_accepts_value(self, mock_config):
        """Test jira_url validation accepts valid URL."""
        # Arrange
        config_data = mock_config(jira_url="https://company.atlassian.net")

        # Act
        config = Config(**config_data)

        # Assert
        assert config.jira_url == "https://company.atlassian.net"

    def test_timeout_validation_positive_integer_accepts_value(self, mock_config):
        """Test timeout validation accepts positive integer."""
        # Arrange
        config_data = mock_config(timeout=60)

        # Act
        config = Config(**config_data)

        # Assert
        assert config.timeout == 60

    def test_max_retries_validation_zero_accepts_value(self, mock_config):
        """Test max_retries validation accepts zero."""
        # Arrange
        config_data = mock_config(max_retries=0)

        # Act
        config = Config(**config_data)

        # Assert
        assert config.max_retries == 0


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.io
class TestLoadConfig:
    """Test load_config function."""

    def test_load_config_from_env_valid_env_vars_returns_config(self, temp_env, monkeypatch):
        """Test load_config from environment variables returns config."""
        # Arrange
        temp_env(
            LEDZEPHYR_JIRA_URL="https://example.atlassian.net",
            LEDZEPHYR_JIRA_USERNAME="demo@example.com",
            LEDZEPHYR_JIRA_API_TOKEN="token123",
            LEDZEPHYR_ZEPHYR_URL="https://zephyr.example.com",
            LEDZEPHYR_ZEPHYR_TOKEN="zephyr_token",
            LEDZEPHYR_QTEST_URL="https://qtest.example.com",
            LEDZEPHYR_QTEST_TOKEN="qtest_token",
        )

        # Act
        config = load_config()

        # Assert
        assert config.jira_url == "https://example.atlassian.net"
        assert config.jira_username == "demo@example.com"
        assert config.jira_api_token == "token123"

    def test_load_config_from_dotenv_valid_file_returns_config(self, temp_env, tmp_path):
        """Test load_config from .env file returns config."""
        # Arrange
        env_file = tmp_path / ".env"
        env_file.write_text(
            "LEDZEPHYR_JIRA_URL=https://dotenv.atlassian.net\n"
            "LEDZEPHYR_JIRA_USERNAME=dotenv@example.com\n"
            "LEDZEPHYR_JIRA_API_TOKEN=dotenv_token\n"
            "LEDZEPHYR_ZEPHYR_URL=https://zephyr.example.com\n"
            "LEDZEPHYR_ZEPHYR_TOKEN=zephyr_token\n"
            "LEDZEPHYR_QTEST_URL=https://qtest.example.com\n"
            "LEDZEPHYR_QTEST_TOKEN=qtest_token\n"
        )

        # Act
        config = load_config(str(env_file))

        # Assert
        assert config.jira_url == "https://dotenv.atlassian.net"
        assert config.jira_username == "dotenv@example.com"
        assert config.jira_api_token == "dotenv_token"

    def test_load_config_nonexistent_file_missing_required_raises_error(self, monkeypatch):
        """Test load_config with nonexistent file and missing required vars raises error."""
        # Arrange
        nonexistent_file = "/path/that/does/not/exist/.env"
        # Clear required environment variables completely
        for key in ["LEDZEPHYR_JIRA_URL", "LEDZEPHYR_JIRA_USERNAME", "LEDZEPHYR_JIRA_API_TOKEN"]:
            monkeypatch.delenv(key, raising=False)

        # Act & Assert
        with pytest.raises(
            ValidationError
        ):  # Should raise validation error for missing required fields
            load_config(nonexistent_file)

    def test_load_config_env_overrides_dotenv_env_wins(self, temp_env, tmp_path):
        """Test load_config environment variables override .env file."""
        # Arrange
        env_file = tmp_path / ".env"
        env_file.write_text(
            "LEDZEPHYR_JIRA_URL=https://dotenv.atlassian.net\n"
            "LEDZEPHYR_JIRA_USERNAME=dotenv@example.com\n"
            "LEDZEPHYR_JIRA_API_TOKEN=dotenv_token\n"
            "LEDZEPHYR_ZEPHYR_URL=https://zephyr.example.com\n"
            "LEDZEPHYR_ZEPHYR_TOKEN=zephyr_token\n"
            "LEDZEPHYR_QTEST_URL=https://qtest.example.com\n"
            "LEDZEPHYR_QTEST_TOKEN=qtest_token\n"
        )

        # Environment variables should override .env
        temp_env(
            LEDZEPHYR_JIRA_URL="https://env.atlassian.net",
            LEDZEPHYR_JIRA_USERNAME="env@example.com",
            LEDZEPHYR_JIRA_API_TOKEN="env_token",
        )

        # Act
        config = load_config(str(env_file))

        # Assert
        assert config.jira_url == "https://env.atlassian.net"
        assert config.jira_username == "env@example.com"
        assert config.jira_api_token == "env_token"

    def test_load_config_optional_vars_defaults_uses_defaults(self, temp_env):
        """Test load_config with only required vars uses defaults for optional."""
        # Arrange
        temp_env(
            LEDZEPHYR_JIRA_URL="https://minimal.atlassian.net",
            LEDZEPHYR_JIRA_USERNAME="minimal@example.com",
            LEDZEPHYR_JIRA_API_TOKEN="minimal_token",
            LEDZEPHYR_ZEPHYR_URL="https://zephyr.example.com",
            LEDZEPHYR_ZEPHYR_TOKEN="zephyr_token",
            LEDZEPHYR_QTEST_URL="https://qtest.example.com",
            LEDZEPHYR_QTEST_TOKEN="qtest_token",
        )

        # Act
        config = load_config()

        # Assert
        assert config.timeout == 30  # Default value
        assert config.max_retries == 3  # Default value
        assert config.log_level == "INFO"  # Default value
