"""Simple API response cache to avoid repeated Jira calls."""

from pathlib import Path
from typing import Any

import requests_cache


class SimpleAPICache:
    """Simple cache for API responses to avoid rate limiting."""

    def __init__(self, cache_dir: str = ".ledzephyr_cache", ttl_hours: int = 24):
        """Initialize cache with basic settings."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl_seconds = ttl_hours * 3600

        # Setup requests-cache for HTTP caching
        cache_file = self.cache_dir / "http_cache"
        self.session = requests_cache.CachedSession(
            cache_name=str(cache_file), backend="sqlite", expire_after=self.ttl_seconds
        )

    def get_cached_response(self, url: str, headers: dict[str, str]) -> dict[str, Any] | None:
        """Get cached API response if available and not expired."""
        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.session.cache.clear()

    def clear_project_cache(self, project_key: str) -> None:
        """Clear cache for a specific project."""
        # For simplicity, clear all cache when project cache is requested
        # Could be made more granular if needed
        self.clear_cache()


_cache_instance: SimpleAPICache | None = None


def get_api_cache() -> SimpleAPICache:
    """Get the global API cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SimpleAPICache()
    return _cache_instance
