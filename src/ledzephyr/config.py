"""Configuration management for ledzephyr."""

from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, field_validator
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

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is positive."""
        if v < 0:
            raise ValueError("timeout must be non-negative")
        return v

    @field_validator("max_retries")
    @classmethod
    def validate_max_retries(cls, v: int) -> int:
        """Validate max_retries is non-negative."""
        if v < 0:
            raise ValueError("max_retries must be non-negative")
        return v

    @field_validator("cache_ttl")
    @classmethod
    def validate_cache_ttl(cls, v: int) -> int:
        """Validate cache_ttl is positive."""
        if v < 0:
            raise ValueError("cache_ttl must be non-negative")
        return v

    @field_validator("cache_size_limit")
    @classmethod
    def validate_cache_size_limit(cls, v: int) -> int:
        """Validate cache_size_limit is positive."""
        if v < 0:
            raise ValueError("cache_size_limit must be non-negative")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log_level is a valid logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()

    @field_validator("jira_url", "zephyr_url", "qtest_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        """Validate URL format."""
        if v is None:
            return v

        if not v.strip():
            raise ValueError("URL cannot be empty")

        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("URL must have scheme (http/https) and domain")

        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL scheme must be http or https")

        return v

    @field_validator("cache_backend")
    @classmethod
    def validate_cache_backend(cls, v: str) -> str:
        """Validate cache_backend is a supported backend."""
        valid_backends = {"sqlite", "memory", "redis"}
        if v not in valid_backends:
            raise ValueError(f"cache_backend must be one of {valid_backends}")
        return v

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> "Config":
        """Load configuration from environment variables and .env file."""
        return load_config(env_file)


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
