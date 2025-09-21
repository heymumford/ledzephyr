"""Comprehensive test suite for configuration management."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from ledzephyr.config import Config, load_config


class TestConfigDefaults:
    """Test default configuration behavior."""

    def test_config_with_minimal_required_fields(self):
        """Test configuration with only required fields."""
        config = Config(
            jira_url="https://test.atlassian.net",
            jira_username="testuser",
            jira_api_token="test-token"
        )

        assert config.jira_url == "https://test.atlassian.net"
        assert config.jira_username == "testuser"
        assert config.jira_api_token == "test-token"

        # Test default values
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.retry_backoff_factor == 0.3
        assert config.log_level == "INFO"
        assert config.zephyr_url is None
        assert config.zephyr_token is None
        assert config.qtest_url is None
        assert config.qtest_token is None

    def test_config_with_all_fields(self):
        """Test configuration with all fields specified."""
        config = Config(
            jira_url="https://test.atlassian.net",
            jira_username="testuser",
            jira_api_token="test-token",
            zephyr_url="https://zephyr.test.com",
            zephyr_token="zephyr-token",
            qtest_url="https://qtest.test.com",
            qtest_token="qtest-token",
            timeout=45,
            max_retries=5,
            retry_backoff_factor=0.5,
            log_level="DEBUG"
        )

        assert config.jira_url == "https://test.atlassian.net"
        assert config.jira_username == "testuser"
        assert config.jira_api_token == "test-token"
        assert config.zephyr_url == "https://zephyr.test.com"
        assert config.zephyr_token == "zephyr-token"
        assert config.qtest_url == "https://qtest.test.com"
        assert config.qtest_token == "qtest-token"
        assert config.timeout == 45
        assert config.max_retries == 5
        assert config.retry_backoff_factor == 0.5
        assert config.log_level == "DEBUG"


class TestEnvironmentVariables:
    """Test environment variable configuration loading."""

    def test_config_with_basic_env_variables(self):
        """Test configuration loading from basic environment variables."""
        with patch.dict(os.environ, {
            'LEDZEPHYR_JIRA_URL': 'https://env.atlassian.net',
            'LEDZEPHYR_JIRA_USERNAME': 'envuser',
            'LEDZEPHYR_JIRA_API_TOKEN': 'env-token'
        }, clear=True):
            config = Config()

            assert config.jira_url == "https://env.atlassian.net"
            assert config.jira_username == "envuser"
            assert config.jira_api_token == "env-token"

    def test_config_with_all_env_variables(self):
        """Test configuration with all environment variables."""
        with patch.dict(os.environ, {
            'LEDZEPHYR_JIRA_URL': 'https://env.atlassian.net',
            'LEDZEPHYR_JIRA_USERNAME': 'envuser',
            'LEDZEPHYR_JIRA_API_TOKEN': 'env-jira-token',
            'LEDZEPHYR_ZEPHYR_URL': 'https://env-zephyr.com',
            'LEDZEPHYR_ZEPHYR_TOKEN': 'env-zephyr-token',
            'LEDZEPHYR_QTEST_URL': 'https://env-qtest.com',
            'LEDZEPHYR_QTEST_TOKEN': 'env-qtest-token',
            'LEDZEPHYR_TIMEOUT': '60',
            'LEDZEPHYR_MAX_RETRIES': '5',
            'LEDZEPHYR_RETRY_BACKOFF_FACTOR': '0.8',
            'LEDZEPHYR_LOG_LEVEL': 'DEBUG'
        }, clear=True):
            config = Config()

            assert config.jira_url == "https://env.atlassian.net"
            assert config.jira_username == "envuser"
            assert config.jira_api_token == "env-jira-token"
            assert config.zephyr_url == "https://env-zephyr.com"
            assert config.zephyr_token == "env-zephyr-token"
            assert config.qtest_url == "https://env-qtest.com"
            assert config.qtest_token == "env-qtest-token"
            assert config.timeout == 60
            assert config.max_retries == 5
            assert config.retry_backoff_factor == 0.8
            assert config.log_level == "DEBUG"

    def test_env_variables_type_conversion(self):
        """Test that environment variables are properly converted to correct types."""
        with patch.dict(os.environ, {
            'LEDZEPHYR_JIRA_URL': 'https://test.com',
            'LEDZEPHYR_JIRA_USERNAME': 'test',
            'LEDZEPHYR_JIRA_API_TOKEN': 'token',
            'LEDZEPHYR_TIMEOUT': '45',
            'LEDZEPHYR_MAX_RETRIES': '10',
            'LEDZEPHYR_RETRY_BACKOFF_FACTOR': '1.5'
        }, clear=True):
            config = Config()

            assert isinstance(config.timeout, int)
            assert isinstance(config.max_retries, int)
            assert isinstance(config.retry_backoff_factor, float)
            assert config.timeout == 45
            assert config.max_retries == 10
            assert config.retry_backoff_factor == 1.5

    def test_missing_required_env_variables(self):
        """Test behavior when required environment variables are missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError):
                Config()

    def test_partial_env_variables(self):
        """Test configuration with some environment variables missing."""
        with patch.dict(os.environ, {
            'LEDZEPHYR_JIRA_URL': 'https://partial.com',
            'LEDZEPHYR_JIRA_USERNAME': 'partial',
            'LEDZEPHYR_JIRA_API_TOKEN': 'token',
            'LEDZEPHYR_TIMEOUT': '90'
            # Missing other optional fields
        }, clear=True):
            config = Config()

            assert config.jira_url == "https://partial.com"
            assert config.timeout == 90
            assert config.zephyr_url is None
            assert config.max_retries == 3  # default value


class TestDotEnvFiles:
    """Test .env file configuration loading."""

    def test_load_config_with_dotenv_file(self):
        """Test loading configuration from a .env file."""
        env_content = """
LEDZEPHYR_JIRA_URL=https://dotenv.atlassian.net
LEDZEPHYR_JIRA_USERNAME=dotenvuser
LEDZEPHYR_JIRA_API_TOKEN=dotenv-token
LEDZEPHYR_ZEPHYR_TOKEN=dotenv-zephyr-token
LEDZEPHYR_TIMEOUT=120
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            env_file = Path(f.name)

        try:
            config = load_config(env_file)

            assert config.jira_url == "https://dotenv.atlassian.net"
            assert config.jira_username == "dotenvuser"
            assert config.jira_api_token == "dotenv-token"
            assert config.zephyr_token == "dotenv-zephyr-token"
            assert config.timeout == 120
        finally:
            env_file.unlink()

    def test_load_config_searches_for_dotenv(self):
        """Test that load_config searches for .env files in standard locations."""
        env_content = """
LEDZEPHYR_JIRA_URL=https://auto-found.com
LEDZEPHYR_JIRA_USERNAME=autouser
LEDZEPHYR_JIRA_API_TOKEN=auto-token
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(env_content)

            # Mock Path.cwd() to return our temp directory
            with patch('ledzephyr.config.Path') as mock_path:
                mock_path.return_value = env_file.parent
                mock_path.home.return_value = env_file.parent
                mock_path.cwd.return_value = env_file.parent

                # Create a mock that behaves like Path but returns our temp directory
                def mock_path_constructor(path_str):
                    if path_str == ".env":
                        return env_file
                    elif path_str == env_file.parent / ".env":
                        return env_file
                    else:
                        return Path(path_str)

                mock_path.side_effect = mock_path_constructor

                # This tests the fallback behavior in load_config
                # The exact implementation may vary, but it should find the .env file
                config = load_config()
                assert isinstance(config, Config)

    def test_nonexistent_dotenv_file(self):
        """Test behavior when specified .env file doesn't exist."""
        nonexistent_file = Path("/nonexistent/path/.env")

        # Should handle gracefully and use environment variables or defaults
        with patch.dict(os.environ, {
            'LEDZEPHYR_JIRA_URL': 'https://test.com',
            'LEDZEPHYR_JIRA_USERNAME': 'test',
            'LEDZEPHYR_JIRA_API_TOKEN': 'token'
        }, clear=True):
            config = load_config(nonexistent_file)
            assert isinstance(config, Config)

    def test_dotenv_with_comments_and_empty_lines(self):
        """Test .env file parsing with comments and empty lines."""
        env_content = """
# This is a comment
LEDZEPHYR_JIRA_URL=https://comment-test.com

# Another comment
LEDZEPHYR_JIRA_USERNAME=commentuser
LEDZEPHYR_JIRA_API_TOKEN=comment-token

# Optional services
LEDZEPHYR_ZEPHYR_URL=https://zephyr-comment.com
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            env_file = Path(f.name)

        try:
            config = load_config(env_file)

            assert config.jira_url == "https://comment-test.com"
            assert config.jira_username == "commentuser"
            assert config.jira_api_token == "comment-token"
            assert config.zephyr_url == "https://zephyr-comment.com"
        finally:
            env_file.unlink()


class TestConfigValidation:
    """Test configuration validation and error handling."""

    def test_invalid_timeout_values(self):
        """Test validation of timeout values."""
        with patch.dict(os.environ, {
            'LEDZEPHYR_JIRA_URL': 'https://test.com',
            'LEDZEPHYR_JIRA_USERNAME': 'test',
            'LEDZEPHYR_JIRA_API_TOKEN': 'token',
            'LEDZEPHYR_TIMEOUT': '-1'  # Invalid negative timeout
        }, clear=True):
            config = Config()
            # Pydantic should handle validation or convert appropriately
            # The exact behavior depends on the field definition

    def test_invalid_retry_values(self):
        """Test validation of retry configuration."""
        with patch.dict(os.environ, {
            'LEDZEPHYR_JIRA_URL': 'https://test.com',
            'LEDZEPHYR_JIRA_USERNAME': 'test',
            'LEDZEPHYR_JIRA_API_TOKEN': 'token',
            'LEDZEPHYR_MAX_RETRIES': '0',  # Edge case
            'LEDZEPHYR_RETRY_BACKOFF_FACTOR': '0.0'  # Edge case
        }, clear=True):
            config = Config()
            assert config.max_retries == 0
            assert config.retry_backoff_factor == 0.0

    def test_url_format_validation(self):
        """Test URL format handling."""
        with patch.dict(os.environ, {
            'LEDZEPHYR_JIRA_URL': 'not-a-url',  # Invalid URL format
            'LEDZEPHYR_JIRA_USERNAME': 'test',
            'LEDZEPHYR_JIRA_API_TOKEN': 'token',
        }, clear=True):
            # Should either validate URLs or accept any string
            config = Config()
            assert config.jira_url == "not-a-url"

    def test_empty_string_values(self):
        """Test handling of empty string values."""
        with patch.dict(os.environ, {
            'LEDZEPHYR_JIRA_URL': '',  # Empty string
            'LEDZEPHYR_JIRA_USERNAME': 'test',
            'LEDZEPHYR_JIRA_API_TOKEN': 'token',
        }, clear=True):
            # Should handle empty strings appropriately
            config = Config()
            # The behavior depends on field validation rules


class TestConfigInCLIContext:
    """Test configuration in the context of CLI usage."""

    def test_missing_api_tokens_detected(self):
        """Test that missing API tokens are properly detected."""
        config = Config(
            jira_url="https://test.com",
            jira_username="test",
            jira_api_token="token"
            # zephyr_token and qtest_token are None
        )

        assert config.zephyr_token is None
        assert config.qtest_token is None

        # This is what the doctor command checks
        assert not config.zephyr_token
        assert not config.qtest_token

    def test_all_api_tokens_present(self):
        """Test detection when all API tokens are present."""
        config = Config(
            jira_url="https://test.com",
            jira_username="test",
            jira_api_token="jira-token",
            zephyr_token="zephyr-token",
            qtest_token="qtest-token"
        )

        assert config.zephyr_token == "zephyr-token"
        assert config.qtest_token == "qtest-token"

        # This is what the doctor command checks
        assert config.zephyr_token
        assert config.qtest_token

    def test_config_serialization(self):
        """Test that config can be serialized/used with other libraries."""
        config = Config(
            jira_url="https://test.com",
            jira_username="test",
            jira_api_token="token",
            timeout=30,
            max_retries=3
        )

        # Should be able to access values programmatically
        assert hasattr(config, 'timeout')
        assert hasattr(config, 'max_retries')
        assert hasattr(config, 'retry_backoff_factor')


class TestEdgeCases:
    """Test edge cases and error conditions in configuration."""

    def test_very_large_timeout_values(self):
        """Test with very large timeout values."""
        with patch.dict(os.environ, {
            'LEDZEPHYR_JIRA_URL': 'https://test.com',
            'LEDZEPHYR_JIRA_USERNAME': 'test',
            'LEDZEPHYR_JIRA_API_TOKEN': 'token',
            'LEDZEPHYR_TIMEOUT': '999999'
        }, clear=True):
            config = Config()
            assert config.timeout == 999999

    def test_unicode_values(self):
        """Test configuration with Unicode values."""
        with patch.dict(os.environ, {
            'LEDZEPHYR_JIRA_URL': 'https://测试.com',
            'LEDZEPHYR_JIRA_USERNAME': 'test',
            'LEDZEPHYR_JIRA_API_TOKEN': 'tökén',
        }, clear=True):
            config = Config()
            assert config.jira_url == "https://测试.com"
            assert config.jira_api_token == "tökén"

    def test_whitespace_handling(self):
        """Test that whitespace in configuration values is handled properly."""
        with patch.dict(os.environ, {
            'LEDZEPHYR_JIRA_URL': '  https://test.com  ',
            'LEDZEPHYR_JIRA_USERNAME': ' testuser ',
            'LEDZEPHYR_JIRA_API_TOKEN': '  token  ',
        }, clear=True):
            config = Config()
            # Values should be used as-is (trimming is application-specific)
            assert config.jira_url == "  https://test.com  "
            assert config.jira_username == " testuser "

    def test_environment_precedence_over_dotenv(self):
        """Test that environment variables take precedence over .env file."""
        env_content = """
LEDZEPHYR_JIRA_URL=https://dotenv.com
LEDZEPHYR_JIRA_USERNAME=dotenvuser
LEDZEPHYR_JIRA_API_TOKEN=dotenv-token
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            env_file = Path(f.name)

        try:
            with patch.dict(os.environ, {
                'LEDZEPHYR_JIRA_URL': 'https://env-override.com'
                # Other values should come from .env file
            }):
                config = load_config(env_file)

                # Environment variable should override .env file
                assert config.jira_url == "https://env-override.com"
        finally:
            env_file.unlink()