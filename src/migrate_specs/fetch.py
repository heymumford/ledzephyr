"""Fetch and validate OpenAPI specifications."""

from __future__ import annotations

from pathlib import Path

import httpx
from openapi_spec_validator import validate_spec
from prance import ResolvingParser

from .config import SPECS_DIR, ApiSpec


def fetch_spec(spec: ApiSpec) -> Path:
    """
    Fetch an API specification, cache it locally, and validate it.

    Args:
        spec: API specification configuration

    Returns:
        Path to the cached specification file

    Raises:
        httpx.HTTPError: If download fails
        ValidationError: If OpenAPI spec is invalid
    """
    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    dest = SPECS_DIR / spec.filename

    # Download if not cached
    if not dest.exists():
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            response = client.get(spec.url)
            response.raise_for_status()
            dest.write_bytes(response.content)

    # Validate OpenAPI specification
    parser = ResolvingParser(str(dest))
    validate_spec(parser.specification)  # raises on invalid

    return dest
