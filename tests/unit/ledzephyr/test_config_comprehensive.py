"""Comprehensive unit tests for configuration module following TDD methodology.

This test suite aims to achieve 80%+ coverage by testing edge cases, error conditions,
and comprehensive validation scenarios for the config module.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from ledzephyr.config import Config, load_config


@pytest.mark.unit
@pytest.mark.auth
class TestConfigValidationEdgeCases:
    """Test Config class validation edge cases and error handling."""

    def test_config_missing_all_required_fields_raises_validation_error(
        self, monkeypatch, tmp_path
    ):
        """Test creating Config without required fields raises ValidationError."""
        # Arrange - clean environment from all LEDZEPHYR vars and move to temp dir
        for key in list(os.environ.keys()):
            if key.startswith("LEDZEPHYR_"):
                monkeypatch.delenv(key, raising=False)

        monkeypatch.chdir(tmp_path)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Config()

        # Verify that all required fields are mentioned in the error
        error_details = str(exc_info.value)
        assert "jira_url" in error_details
        assert "jira_username" in error_details
        assert "jira_api_token" in error_details

    def test_config_partial_required_fields_raises_validation_error(self, monkeypatch, tmp_path):
        """Test creating Config with only some required fields raises ValidationError."""
        # Arrange - clean environment and move to temp dir
        for key in list(os.environ.keys()):
            if key.startswith("LEDZEPHYR_"):
                monkeypatch.delenv(key, raising=False)

        monkeypatch.chdir(tmp_path)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Config(jira_url="https://test.atlassian.net")

        # Verify that missing required fields are mentioned
        error_details = str(exc_info.value)
        assert "jira_username" in error_details
        assert "jira_api_token" in error_details

    def test_config_invalid_timeout_negative_raises_validation_error(self):
        """Test Config with negative timeout raises ValidationError."""
        # This test should fail initially - negative timeout validation doesn't exist yet
        with pytest.raises(ValidationError):
            Config(
                jira_url="https://test.atlassian.net",
                jira_username="test@example.com",
                jira_api_token="token",
                timeout=-1,
            )

    def test_config_invalid_max_retries_negative_raises_validation_error(self):
        """Test Config with negative max_retries raises ValidationError."""
        # This test should fail initially - negative max_retries validation doesn't exist yet
        with pytest.raises(ValidationError):
            Config(
                jira_url="https://test.atlassian.net",
                jira_username="test@example.com",
                jira_api_token="token",
                max_retries=-1,
            )

    def test_config_invalid_cache_ttl_negative_raises_validation_error(self):
        """Test Config with negative cache_ttl raises ValidationError."""
        # This test should fail initially - negative cache_ttl validation doesn't exist yet
        with pytest.raises(ValidationError):
            Config(
                jira_url="https://test.atlassian.net",
                jira_username="test@example.com",
                jira_api_token="token",
                cache_ttl=-1,
            )

    def test_config_invalid_cache_size_limit_negative_raises_validation_error(self):
        """Test Config with negative cache_size_limit raises ValidationError."""
        # This test should fail initially - negative cache_size_limit validation doesn't exist yet
        with pytest.raises(ValidationError):
            Config(
                jira_url="https://test.atlassian.net",
                jira_username="test@example.com",
                jira_api_token="token",
                cache_size_limit=-1,
            )

    def test_config_invalid_log_level_raises_validation_error(self):
        """Test Config with invalid log level raises ValidationError."""
        # This test should fail initially - log level validation doesn't exist yet
        with pytest.raises(ValidationError):
            Config(
                jira_url="https://test.atlassian.net",
                jira_username="test@example.com",
                jira_api_token="token",
                log_level="INVALID_LEVEL",
            )


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.io
class TestLoadConfigPathResolution:
    """Test load_config function file path resolution and fallback logic."""

    def test_load_config_with_pathlib_path_object_resolves_correctly(self, tmp_path):
        """Test load_config accepts pathlib.Path objects."""
        # Arrange
        env_file = tmp_path / "test.env"
        env_file.write_text(
            "LEDZEPHYR_JIRA_URL=https://pathlib.atlassian.net\n"
            "LEDZEPHYR_JIRA_USERNAME=pathlib@example.com\n"
            "LEDZEPHYR_JIRA_API_TOKEN=pathlib_token\n"
        )

        # Act
        config = load_config(env_file)

        # Assert
        assert config.jira_url == "https://pathlib.atlassian.net"
        assert config.jira_username == "pathlib@example.com"
        assert config.jira_api_token == "pathlib_token"

    def test_load_config_home_directory_env_file_fallback_works(self, monkeypatch, tmp_path):
        """Test load_config falls back to home directory .env file."""
        # This test should fail initially as we need to mock home directory behavior
        # Arrange
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        env_file = fake_home / ".env"
        env_file.write_text(
            "LEDZEPHYR_JIRA_URL=https://home.atlassian.net\n"
            "LEDZEPHYR_JIRA_USERNAME=home@example.com\n"
            "LEDZEPHYR_JIRA_API_TOKEN=home_token\n"
        )

        # Change to a directory without .env and mock home
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        monkeypatch.chdir(work_dir)

        with patch.object(Path, "home", return_value=fake_home):
            # Act
            config = load_config()

            # Assert
            assert config.jira_url == "https://home.atlassian.net"
            assert config.jira_username == "home@example.com"
            assert config.jira_api_token == "home_token"

    def test_load_config_current_directory_takes_precedence_over_home(self, monkeypatch, tmp_path):
        """Test load_config prefers current directory .env over home directory."""
        # Arrange
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        home_env = fake_home / ".env"
        home_env.write_text(
            "LEDZEPHYR_JIRA_URL=https://home.atlassian.net\n"
            "LEDZEPHYR_JIRA_USERNAME=home@example.com\n"
            "LEDZEPHYR_JIRA_API_TOKEN=home_token\n"
        )

        work_dir = tmp_path / "work"
        work_dir.mkdir()
        current_env = work_dir / ".env"
        current_env.write_text(
            "LEDZEPHYR_JIRA_URL=https://current.atlassian.net\n"
            "LEDZEPHYR_JIRA_USERNAME=current@example.com\n"
            "LEDZEPHYR_JIRA_API_TOKEN=current_token\n"
        )

        monkeypatch.chdir(work_dir)

        with patch.object(Path, "home", return_value=fake_home):
            # Act
            config = load_config()

            # Assert - should use current directory, not home
            assert config.jira_url == "https://current.atlassian.net"
            assert config.jira_username == "current@example.com"
            assert config.jira_api_token == "current_token"


@pytest.mark.unit
@pytest.mark.auth
class TestEnvironmentVariableHandling:
    """Test environment variable substitution and precedence."""

    def test_env_vars_override_env_file_values(self, temp_env, tmp_path):
        """Test environment variables take precedence over .env file values."""
        # Arrange
        env_file = tmp_path / ".env"
        env_file.write_text(
            "LEDZEPHYR_JIRA_URL=https://file.atlassian.net\n"
            "LEDZEPHYR_JIRA_USERNAME=file@example.com\n"
            "LEDZEPHYR_JIRA_API_TOKEN=file_token\n"
            "LEDZEPHYR_TIMEOUT=60\n"
        )

        temp_env(LEDZEPHYR_JIRA_URL="https://env.atlassian.net", LEDZEPHYR_TIMEOUT="45")

        # Act
        config = load_config(str(env_file))

        # Assert - env vars should override file values
        assert config.jira_url == "https://env.atlassian.net"  # from env var
        assert config.jira_username == "file@example.com"  # from file
        assert config.jira_api_token == "file_token"  # from file
        assert config.timeout == 45  # from env var

    def test_config_handles_boolean_env_vars_correctly(self, temp_env):
        """Test boolean environment variables are parsed correctly."""
        # Arrange
        temp_env(
            LEDZEPHYR_JIRA_URL="https://bool.atlassian.net",
            LEDZEPHYR_JIRA_USERNAME="bool@example.com",
            LEDZEPHYR_JIRA_API_TOKEN="bool_token",
            LEDZEPHYR_CACHE_ENABLED="false",
        )

        # Act
        config = load_config()

        # Assert
        assert config.cache_enabled is False

    def test_config_handles_integer_env_vars_correctly(self, temp_env):
        """Test integer environment variables are parsed correctly."""
        # Arrange
        temp_env(
            LEDZEPHYR_JIRA_URL="https://int.atlassian.net",
            LEDZEPHYR_JIRA_USERNAME="int@example.com",
            LEDZEPHYR_JIRA_API_TOKEN="int_token",
            LEDZEPHYR_TIMEOUT="120",
            LEDZEPHYR_MAX_RETRIES="5",
            LEDZEPHYR_CACHE_TTL="7200",
        )

        # Act
        config = load_config()

        # Assert
        assert config.timeout == 120
        assert config.max_retries == 5
        assert config.cache_ttl == 7200


@pytest.mark.unit
@pytest.mark.auth
class TestMalformedConfigurationHandling:
    """Test configuration validation with malformed data."""

    def test_load_config_malformed_env_file_raises_error(self, tmp_path, monkeypatch):
        """Test load_config with malformed .env file raises appropriate error."""
        # This test should fail initially - need to handle malformed env files
        # Arrange
        env_file = tmp_path / "malformed.env"
        env_file.write_text("INVALID_FORMAT_NO_EQUALS_SIGN")

        monkeypatch.chdir(tmp_path)

        # Act & Assert
        with pytest.raises(Exception):  # Should raise some kind of parsing error
            load_config(str(env_file))

    def test_config_invalid_url_format_raises_validation_error(self):
        """Test Config with invalid URL format raises ValidationError."""
        # This test should fail initially - URL validation doesn't exist yet
        with pytest.raises(ValidationError):
            Config(
                jira_url="not-a-valid-url", jira_username="test@example.com", jira_api_token="token"
            )

    def test_config_empty_required_string_raises_validation_error(self):
        """Test Config with empty required strings raises ValidationError."""
        # This test should fail initially - empty string validation doesn't exist yet
        with pytest.raises(ValidationError):
            Config(jira_url="", jira_username="test@example.com", jira_api_token="token")

    def test_config_invalid_url_scheme_raises_validation_error(self):
        """Test Config with invalid URL scheme raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Config(
                jira_url="ftp://test.atlassian.net",
                jira_username="test@example.com",
                jira_api_token="token",
            )

        error_details = str(exc_info.value)
        assert "URL scheme must be http or https" in error_details


@pytest.mark.unit
@pytest.mark.auth
class TestConfigFromEnvClassMethod:
    """Test the Config.from_env class method."""

    def test_config_from_env_delegates_to_load_config(self, temp_env):
        """Test Config.from_env delegates to load_config function."""
        # Arrange
        temp_env(
            LEDZEPHYR_JIRA_URL="https://fromenv.atlassian.net",
            LEDZEPHYR_JIRA_USERNAME="fromenv@example.com",
            LEDZEPHYR_JIRA_API_TOKEN="fromenv_token",
        )

        # Act
        config = Config.from_env()

        # Assert
        assert config.jira_url == "https://fromenv.atlassian.net"
        assert config.jira_username == "fromenv@example.com"
        assert config.jira_api_token == "fromenv_token"

    def test_config_from_env_with_file_path_works(self, tmp_path):
        """Test Config.from_env with specific env file path."""
        # Arrange
        env_file = tmp_path / "specific.env"
        env_file.write_text(
            "LEDZEPHYR_JIRA_URL=https://specific.atlassian.net\n"
            "LEDZEPHYR_JIRA_USERNAME=specific@example.com\n"
            "LEDZEPHYR_JIRA_API_TOKEN=specific_token\n"
        )

        # Act
        config = Config.from_env(env_file)

        # Assert
        assert config.jira_url == "https://specific.atlassian.net"
        assert config.jira_username == "specific@example.com"
        assert config.jira_api_token == "specific_token"


@pytest.mark.unit
@pytest.mark.auth
class TestCacheConfigurationValidation:
    """Test cache configuration field validation."""

    def test_config_valid_cache_backend_accepts_sqlite(self, mock_config):
        """Test Config accepts valid cache backend."""
        # Arrange
        config_data = mock_config(cache_backend="sqlite")

        # Act
        config = Config(**config_data)

        # Assert
        assert config.cache_backend == "sqlite"

    def test_config_valid_cache_backend_accepts_memory(self, mock_config):
        """Test Config accepts memory cache backend."""
        # Arrange
        config_data = mock_config(cache_backend="memory")

        # Act
        config = Config(**config_data)

        # Assert
        assert config.cache_backend == "memory"

    def test_config_invalid_cache_backend_raises_validation_error(self, mock_config):
        """Test Config with invalid cache backend raises ValidationError."""
        # This test should fail initially - cache backend validation doesn't exist yet
        with pytest.raises(ValidationError):
            Config(**mock_config(cache_backend="invalid_backend"))

    def test_config_cache_dir_path_validation(self, mock_config):
        """Test Config cache directory path validation."""
        # Arrange
        config_data = mock_config(cache_dir="/valid/path/to/cache")

        # Act
        config = Config(**config_data)

        # Assert
        assert config.cache_dir == "/valid/path/to/cache"
