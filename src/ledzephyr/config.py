"""Configuration management for ledzephyr."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Configuration for ledzephyr CLI tool."""

    # API Configuration
    jira_url: str = Field(..., description="Jira instance URL")
    jira_username: str = Field(..., description="Jira username")
    jira_api_token: str = Field(..., description="Jira API token")

    zephyr_url: str | None = Field(None, description="Zephyr Scale API URL")
    zephyr_token: str | None = Field(None, description="Zephyr Scale API token")

    qtest_url: str | None = Field(None, description="qTest API URL")
    qtest_token: str | None = Field(None, description="qTest API token")

    # HTTP Configuration
    timeout: int = Field(30, description="HTTP request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries for HTTP requests")
    retry_backoff_factor: float = Field(0.3, description="Backoff factor for retries")

    # Logging
    log_level: str = Field("INFO", description="Logging level")

    # Cache Configuration
    cache_enabled: bool = Field(True, description="Enable caching")
    cache_ttl: int = Field(3600, description="Default cache TTL in seconds")
    cache_backend: str = Field("sqlite", description="Cache backend")
    cache_dir: str = Field(".tool_cache", description="Cache directory")
    cache_size_limit: int = Field(1073741824, description="Cache size limit in bytes")  # 1 GiB

    model_config = SettingsConfigDict(
        env_prefix="LEDZEPHYR_",
        env_file=".env",
        env_file_encoding="utf-8",
    )


def load_config(env_file: str | Path | None = None) -> Config:
    """Load configuration from environment variables and .env file."""
    # If a specific env file is provided, use it
    if env_file:
        env_path = Path(env_file) if isinstance(env_file, str) else env_file
        if env_path.exists():
            # Create a custom config class with the specific env file
            class CustomConfig(Config):
                model_config = SettingsConfigDict(
                    env_prefix="LEDZEPHYR_",
                    env_file=str(env_path),
                    env_file_encoding="utf-8",
                )

            return CustomConfig()

    # Try to find .env file in current directory or home directory
    for env_path in [Path(".env"), Path.home() / ".env"]:
        if env_path.exists():
            # Create a custom config class with the found env file
            class FoundEnvConfig(Config):
                model_config = SettingsConfigDict(
                    env_prefix="LEDZEPHYR_",
                    env_file=str(env_path),
                    env_file_encoding="utf-8",
                )

            return FoundEnvConfig()

    # Fall back to default config (loads from environment only)
    return Config()
