"""
Hypothesis strategies for configuration data.
"""

from hypothesis import strategies as st
from typing import Dict, Any


@st.composite
def valid_urls(draw) -> str:
    """Generate valid URL strings."""
    protocols = ["http", "https"]
    domains = [
        "example.com",
        "test.atlassian.net",
        "company.jira.com",
        "localhost",
        "127.0.0.1",
    ]

    protocol = draw(st.sampled_from(protocols))
    domain = draw(st.sampled_from(domains))

    # Optionally add port
    port = draw(st.one_of(
        st.just(""),
        st.just(":8080"),
        st.just(":3000"),
        st.integers(min_value=1024, max_value=65535).map(lambda p: f":{p}")
    ))

    return f"{protocol}://{domain}{port}"


@st.composite
def api_tokens(draw) -> str:
    """Generate realistic API tokens."""
    # Various token formats used by different services
    token_types = [
        # Jira API tokens (base64-like)
        st.text(
            alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=",
            min_size=20,
            max_size=100
        ),
        # Simple alphanumeric tokens
        st.text(
            alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
            min_size=32,
            max_size=64
        ),
        # Hex tokens
        st.text(
            alphabet="0123456789abcdef",
            min_size=32,
            max_size=128
        ),
    ]

    return draw(st.one_of(token_types))


@st.composite
def usernames(draw) -> str:
    """Generate realistic usernames."""
    return draw(st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789._-",
        min_size=3,
        max_size=50
    ).filter(lambda x: x[0].isalpha()))  # Must start with letter


@st.composite
def config_data(draw) -> Dict[str, Any]:
    """Generate complete configuration data."""
    return {
        "jira_url": draw(valid_urls()),
        "jira_username": draw(usernames()),
        "jira_token": draw(api_tokens()),
        "zephyr_url": draw(valid_urls()),
        "zephyr_token": draw(api_tokens()),
        "qtest_url": draw(valid_urls()),
        "qtest_token": draw(api_tokens()),
        "log_level": draw(st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])),
        "timeout": draw(st.integers(min_value=1, max_value=300)),
        "max_retries": draw(st.integers(min_value=0, max_value=10)),
    }


@st.composite
def environment_variables(draw) -> Dict[str, str]:
    """Generate environment variable dictionaries."""
    config = draw(config_data())

    return {
        "LEDZEPHYR_JIRA_URL": config["jira_url"],
        "LEDZEPHYR_JIRA_USERNAME": config["jira_username"],
        "LEDZEPHYR_JIRA_TOKEN": config["jira_token"],
        "LEDZEPHYR_ZEPHYR_URL": config["zephyr_url"],
        "LEDZEPHYR_ZEPHYR_TOKEN": config["zephyr_token"],
        "LEDZEPHYR_QTEST_URL": config["qtest_url"],
        "LEDZEPHYR_QTEST_TOKEN": config["qtest_token"],
        "LEDZEPHYR_LOG_LEVEL": config["log_level"],
        "LEDZEPHYR_TIMEOUT": str(config["timeout"]),
        "LEDZEPHYR_MAX_RETRIES": str(config["max_retries"]),
    }