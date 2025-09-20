"""Test configuration management."""

import pytest
from pathlib import Path
from unittest.mock import patch

from ledzephyr.config import Config, load_config


def test_config_defaults():
    """Test default configuration values."""
    config = Config(
        jira_url="https://test.atlassian.net",
        jira_username="testuser",
        jira_api_token="test-token"
    )
    
    assert config.jira_url == "https://test.atlassian.net"
    assert config.jira_username == "testuser"
    assert config.jira_api_token == "test-token"
    assert config.timeout == 30
    assert config.max_retries == 3
    assert config.retry_backoff_factor == 0.3
    assert config.log_level == "INFO"


def test_config_with_env_variables():
    """Test configuration loading from environment variables."""
    with patch.dict('os.environ', {
        'LEDZEPHYR_JIRA_URL': 'https://env.atlassian.net',
        'LEDZEPHYR_JIRA_USERNAME': 'envuser',
        'LEDZEPHYR_JIRA_API_TOKEN': 'env-token',
        'LEDZEPHYR_TIMEOUT': '60',
        'LEDZEPHYR_MAX_RETRIES': '5'
    }):
        config = Config()
        
        assert config.jira_url == "https://env.atlassian.net"
        assert config.jira_username == "envuser"
        assert config.jira_api_token == "env-token"
        assert config.timeout == 60
        assert config.max_retries == 5


def test_load_config():
    """Test configuration loading function."""
    with patch.dict('os.environ', {
        'LEDZEPHYR_JIRA_URL': 'https://load.atlassian.net',
        'LEDZEPHYR_JIRA_USERNAME': 'loaduser',
        'LEDZEPHYR_JIRA_API_TOKEN': 'load-token'
    }):
        config = load_config()
        
        assert isinstance(config, Config)
        assert config.jira_url == "https://load.atlassian.net"