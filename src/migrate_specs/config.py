"""Configuration for pinned API versions and spec URLs."""

from dataclasses import dataclass
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SPECS_DIR = BASE / "specs"
GOLD_DIR = BASE / "gold"


@dataclass(frozen=True)
class ApiSpec:
    """API specification configuration."""

    name: str
    version: str  # pinned
    url: str  # OpenAPI JSON/YAML URL or file path
    filename: str  # local cache name


# Pinned API specifications
JIRA = ApiSpec(
    "jira",
    "v3",
    "https://raw.githubusercontent.com/atlassian/openapi/main/jira-platform-rest-api-v3.yaml",
    "jira-v3.yaml",
)

ZEPHYR = ApiSpec(
    "zephyr",
    "v2",
    "https://raw.githubusercontent.com/SmartBear/zephyr-scale-server-api-docs/main/openapi.yaml",
    "zephyr-v2.yaml",
)

QTEST = ApiSpec(
    "qtest",
    "v3",
    "https://documentation.tricentis.com/qtest/od/en/content/resources/qtest_api_specification.json",
    "qtest-v3.json",
)

ALL = [JIRA, ZEPHYR, QTEST]
