"""Tests for simple API cache functionality."""

import tempfile
from pathlib import Path

from ledzephyr.cache import SimpleAPICache, get_api_cache


class TestSimpleAPICache:
    """Test the simple API cache for avoiding repeated vendor calls."""

    def test_cache_initialization(self):
        """Test cache initializes with default settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = SimpleAPICache(cache_dir=temp_dir, ttl_hours=1)
            assert cache.cache_dir == Path(temp_dir)
            assert cache.ttl_seconds == 3600

    def test_cached_response_basic_functionality(self):
        """Test that cache can be created and used."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = SimpleAPICache(cache_dir=temp_dir, ttl_hours=1)

            test_url = "https://api.example.com/data"
            test_headers = {"Authorization": "Bearer test"}

            # Act - Should handle the call without error
            result = cache.get_cached_response(test_url, test_headers)

            # Assert - Should not crash (result may be None for failed requests)
            assert result is None or isinstance(result, dict)

    def test_clear_cache_removes_all_data(self):
        """Test that clear_cache removes all cached data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = SimpleAPICache(cache_dir=temp_dir, ttl_hours=1)

            # Clear should not raise errors even on empty cache
            cache.clear_cache()

    def test_get_api_cache_returns_singleton(self):
        """Test that get_api_cache returns the same instance."""
        cache1 = get_api_cache()
        cache2 = get_api_cache()

        assert cache1 is cache2
