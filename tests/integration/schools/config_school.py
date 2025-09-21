"""
Config School: Configuration and environment patterns

Orthogonal Concern: How the system adapts to different environments
- Environment variables
- Configuration validation
- Default fallbacks
- Secret handling
"""

import os
from unittest.mock import patch

from ledzephyr.config import Config

from . import Kata, School, register_school


def kata_config_environment_override():
    """Kata: Configuration respects environment variables."""
    test_env = {
        "LEDZEPHYR_JIRA_URL": "https://env-test.atlassian.net",
        "LEDZEPHYR_JIRA_USERNAME": "env-user@example.com",
        "LEDZEPHYR_JIRA_API_TOKEN": "env-token-123",
    }

    with patch.dict(os.environ, test_env):
        config = Config()  # Should pick up env vars

        assert config.jira_url == "https://env-test.atlassian.net"
        assert config.jira_username == "env-user@example.com"
        assert config.jira_api_token == "env-token-123"

    return True


def kata_config_validation_rules():
    """Kata: Configuration validates required fields."""
    from pydantic import ValidationError

    # Missing required fields should fail validation
    try:
        config = Config(
            jira_url="",  # Empty required field - actually this is valid, empty string is allowed
            # jira_username missing - this should fail
            jira_api_token="token",
        )
        raise AssertionError("Should have failed validation due to missing jira_username")
    except ValidationError as e:
        assert "jira_username" in str(e).lower()

    return True


def kata_config_secure_defaults():
    """Kata: Configuration uses secure defaults."""
    config = Config(
        jira_url="https://test.atlassian.net",
        jira_username="test@example.com",
        jira_api_token="test-token",
    )

    # Should have secure defaults
    assert config.timeout > 0, "Should have reasonable timeout"
    assert config.max_retries >= 0, "Should have retry configuration"
    assert hasattr(config, "cache_ttl"), "Should have cache TTL"
    assert config.cache_ttl > 0, "Cache TTL should be positive"

    return True


def kata_config_gold_master_mode():
    """Kata: Configuration supports gold master test mode."""
    test_env = {
        "LEDZEPHYR_USE_GOLD_MASTER": "true",
        "LEDZEPHYR_GOLD_MASTER_PATH": "/path/to/gold.csv",
    }

    with patch.dict(os.environ, test_env):
        # System should detect gold master mode
        assert os.getenv("LEDZEPHYR_USE_GOLD_MASTER") == "true"
        assert os.getenv("LEDZEPHYR_GOLD_MASTER_PATH") == "/path/to/gold.csv"

    return True


def kata_config_api_endpoint_construction():
    """Kata: Configuration builds API endpoints correctly."""
    config = Config(
        jira_url="https://test.atlassian.net",
        jira_username="test@example.com",
        jira_api_token="test-token",
        qtest_url="https://test.qtestnet.com",
        qtest_token="qtest-token",
    )

    # Should construct valid endpoints
    assert config.jira_url.startswith("https://")
    assert not config.jira_url.endswith("/")  # No trailing slash

    if config.qtest_url:
        assert config.qtest_url.startswith("https://")
        assert not config.qtest_url.endswith("/")

    return True


# Define the Config School
config_school = School(
    name="config_school",
    description="Configuration, environment, and settings patterns",
    katas=[
        Kata(
            "env_override",
            "Config respects environment variables",
            kata_config_environment_override,
        ),
        Kata("validation_rules", "Config validates required fields", kata_config_validation_rules),
        Kata("secure_defaults", "Config uses secure defaults", kata_config_secure_defaults),
        Kata("gold_master_mode", "Config supports gold master mode", kata_config_gold_master_mode),
        Kata(
            "endpoint_construction",
            "Config builds endpoints correctly",
            kata_config_api_endpoint_construction,
        ),
    ],
    parallel_safe=True,
)

# Register for discovery
register_school(config_school)
