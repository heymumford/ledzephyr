"""Configuration management for ledzephyr."""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Configuration for ledzephyr CLI tool."""
    
    # API Configuration
    jira_url: str = Field(..., description="Jira instance URL")
    jira_username: str = Field(..., description="Jira username")
    jira_api_token: str = Field(..., description="Jira API token")
    
    zephyr_url: Optional[str] = Field(None, description="Zephyr Scale API URL")
    zephyr_token: Optional[str] = Field(None, description="Zephyr Scale API token")
    
    qtest_url: Optional[str] = Field(None, description="qTest API URL")
    qtest_token: Optional[str] = Field(None, description="qTest API token")
    
    # HTTP Configuration
    timeout: int = Field(30, description="HTTP request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries for HTTP requests")
    retry_backoff_factor: float = Field(0.3, description="Backoff factor for retries")
    
    # Logging
    log_level: str = Field("INFO", description="Logging level")
    
    model_config = {
        "env_prefix": "LEDZEPHYR_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


def load_config(env_file: Optional[Path] = None) -> Config:
    """Load configuration from environment variables and .env file."""
    if env_file and env_file.exists():
        return Config(_env_file=env_file)
    
    # Try to find .env file in current directory or home directory
    for env_path in [Path(".env"), Path.home() / ".env"]:
        if env_path.exists():
            return Config(_env_file=env_path)
    
    return Config()