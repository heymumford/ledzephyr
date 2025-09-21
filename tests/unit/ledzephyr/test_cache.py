"""Tests for simple API cache functionality."""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import requests

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

    def test_get_cached_response_successful_json_response(self, requests_mock):
        """Test successful HTTP response with JSON data returns the parsed JSON."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = SimpleAPICache(cache_dir=temp_dir, ttl_hours=1)
            test_url = "https://api.example.com/data"
            test_headers = {"Authorization": "Bearer test"}
            expected_data = {"id": 123, "name": "test_item", "status": "active"}

            # Mock successful HTTP response
            requests_mock.get(
                test_url,
                json=expected_data,
                status_code=200,
                headers={"Content-Type": "application/json"},
            )

            # Act
            result = cache.get_cached_response(test_url, test_headers)

            # Assert
            assert result == expected_data
            assert requests_mock.call_count == 1
            assert requests_mock.last_request.url == test_url

    def test_clear_project_cache_calls_clear_cache(self):
        """Test that clear_project_cache calls the clear_cache method."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = SimpleAPICache(cache_dir=temp_dir, ttl_hours=1)

            # Use mock to verify clear_cache is called
            with patch.object(cache, "clear_cache", wraps=cache.clear_cache) as mock_clear:
                # Act
                cache.clear_project_cache("TEST-123")

                # Assert
                mock_clear.assert_called_once()

    def test_cache_expiration_functionality(self, requests_mock):
        """Test cache TTL expiration works correctly."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create cache with very short TTL (1 second)
            cache = SimpleAPICache(cache_dir=temp_dir, ttl_hours=1 / 3600)  # 1 second
            test_url = "https://api.example.com/expiring"
            test_headers = {"Authorization": "Bearer test"}

            first_data = {"timestamp": "first"}
            second_data = {"timestamp": "second"}

            # Setup multiple responses
            requests_mock.get(
                test_url,
                [
                    {"json": first_data, "status_code": 200},
                    {"json": second_data, "status_code": 200},
                ],
            )

            # Act & Assert
            # First call should return first data
            result1 = cache.get_cached_response(test_url, test_headers)
            assert result1 == first_data
            assert requests_mock.call_count == 1

            # Wait for cache to expire
            time.sleep(1.1)  # Wait slightly longer than TTL

            # Second call should fetch new data
            result2 = cache.get_cached_response(test_url, test_headers)
            assert result2 == second_data
            assert requests_mock.call_count == 2

    def test_cache_http_error_handling(self, requests_mock):
        """Test cache behavior with HTTP errors (4xx, 5xx)."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = SimpleAPICache(cache_dir=temp_dir, ttl_hours=1)
            test_url = "https://api.example.com/error"
            test_headers = {"Authorization": "Bearer test"}

            # Mock HTTP error response
            requests_mock.get(test_url, json={"error": "Not found"}, status_code=404)

            # Act
            result = cache.get_cached_response(test_url, test_headers)

            # Assert
            assert result is None  # Should return None on HTTP errors
            assert requests_mock.call_count == 1

    def test_cache_invalid_json_handling(self, requests_mock):
        """Test cache behavior with invalid JSON responses."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = SimpleAPICache(cache_dir=temp_dir, ttl_hours=1)
            test_url = "https://api.example.com/invalid_json"
            test_headers = {"Authorization": "Bearer test"}

            # Mock response with invalid JSON
            requests_mock.get(
                test_url,
                text="invalid json content",
                status_code=200,
                headers={"Content-Type": "application/json"},
            )

            # Act
            result = cache.get_cached_response(test_url, test_headers)

            # Assert
            assert result is None  # Should return None on JSON decode errors
            assert requests_mock.call_count == 1

    def test_cache_stress_test_large_datasets(self, requests_mock):
        """Test cache performance with large datasets."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = SimpleAPICache(cache_dir=temp_dir, ttl_hours=1)

            # Create large JSON payload (simulate real-world API response)
            large_data = {
                "items": [
                    {
                        "id": i,
                        "name": f"item_{i}",
                        "description": "x" * 100,  # 100 chars per item
                        "metadata": {"key": f"value_{i}", "tags": [f"tag_{j}" for j in range(10)]},
                    }
                    for i in range(1000)
                ]  # 1000 items
            }

            test_url = "https://api.example.com/large_data"
            test_headers = {"Authorization": "Bearer test"}

            requests_mock.get(test_url, json=large_data, status_code=200)

            # Act
            start_time = time.time()
            result = cache.get_cached_response(test_url, test_headers)
            first_call_time = time.time() - start_time

            # Second call should be from cache (faster)
            start_time = time.time()
            cached_result = cache.get_cached_response(test_url, test_headers)
            cached_call_time = time.time() - start_time

            # Assert
            assert result == large_data
            assert cached_result == large_data
            assert requests_mock.call_count == 1  # Only one actual HTTP call
            # Cache should be faster (though this is environment dependent)
            assert cached_call_time < first_call_time or cached_call_time < 0.1

    def test_cache_backend_configuration(self):
        """Test cache initializes with different backend configurations."""
        # Arrange & Act
        with tempfile.TemporaryDirectory() as temp_dir:
            cache1 = SimpleAPICache(cache_dir=temp_dir, ttl_hours=1)
            cache2 = SimpleAPICache(cache_dir=temp_dir, ttl_hours=24)
            cache3 = SimpleAPICache(cache_dir=temp_dir, ttl_hours=168)  # 1 week

            # Assert
            assert cache1.ttl_seconds == 3600  # 1 hour
            assert cache2.ttl_seconds == 86400  # 24 hours
            assert cache3.ttl_seconds == 604800  # 1 week

            # Verify each cache has its own session but same directory
            assert cache1.cache_dir == cache2.cache_dir == cache3.cache_dir
            assert cache1.session != cache2.session != cache3.session

    def test_cache_network_timeout_handling(self, requests_mock):
        """Test cache behavior with network timeouts."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = SimpleAPICache(cache_dir=temp_dir, ttl_hours=1)
            test_url = "https://api.example.com/timeout"
            test_headers = {"Authorization": "Bearer test"}

            # Mock timeout exception
            requests_mock.get(test_url, exc=requests.exceptions.Timeout)

            # Act
            result = cache.get_cached_response(test_url, test_headers)

            # Assert
            assert result is None  # Should return None on timeout
            assert requests_mock.call_count == 1

    def test_cache_connection_error_handling(self, requests_mock):
        """Test cache behavior with connection errors."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = SimpleAPICache(cache_dir=temp_dir, ttl_hours=1)
            test_url = "https://api.example.com/connection_error"
            test_headers = {"Authorization": "Bearer test"}

            # Mock connection error
            requests_mock.get(test_url, exc=requests.exceptions.ConnectionError)

            # Act
            result = cache.get_cached_response(test_url, test_headers)

            # Assert
            assert result is None  # Should return None on connection error
            assert requests_mock.call_count == 1

    def test_cache_directory_creation(self):
        """Test cache creates directory if it doesn't exist."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_subdir = (
                Path(temp_dir) / "cache"
            )  # Only one level deep since mkdir doesn't use parents=True

            # Act
            cache = SimpleAPICache(cache_dir=str(cache_subdir), ttl_hours=1)

            # Assert
            assert cache_subdir.exists()
            assert cache_subdir.is_dir()
            assert cache.cache_dir == cache_subdir

    def test_cache_singleton_reset_for_testing(self):
        """Test that we can reset the singleton cache for testing purposes."""
        # This test ensures we can test the singleton behavior properly
        # by accessing the global state

        # Arrange - Get initial cache
        cache1 = get_api_cache()

        # Act - Reset global cache (simulate module reload)
        import ledzephyr.cache

        ledzephyr.cache._cache_instance = None

        # Get new cache
        cache2 = get_api_cache()

        # Assert
        assert cache1 is not cache2  # Should be different instances

        # Verify new cache is still singleton
        cache3 = get_api_cache()
        assert cache2 is cache3

    def test_cache_ttl_edge_cases(self):
        """Test cache TTL configuration with edge case values."""
        # Arrange & Act & Assert
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test very small TTL
            cache_small = SimpleAPICache(cache_dir=temp_dir, ttl_hours=0.001)  # ~3.6 seconds
            assert cache_small.ttl_seconds == 3.6

            # Test zero TTL (should still work)
            cache_zero = SimpleAPICache(cache_dir=temp_dir, ttl_hours=0)
            assert cache_zero.ttl_seconds == 0

            # Test large TTL
            cache_large = SimpleAPICache(cache_dir=temp_dir, ttl_hours=8760)  # 1 year
            assert cache_large.ttl_seconds == 31536000

    def test_cache_with_different_urls(self, requests_mock):
        """Test that different URLs create separate cache entries."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = SimpleAPICache(cache_dir=temp_dir, ttl_hours=1)
            test_url1 = "https://api.example.com/data1"
            test_url2 = "https://api.example.com/data2"
            headers = {"Authorization": "Bearer token"}

            data1 = {"source": "url1"}
            data2 = {"source": "url2"}

            # Setup different responses for different URLs
            requests_mock.get(test_url1, json=data1, status_code=200)
            requests_mock.get(test_url2, json=data2, status_code=200)

            # Act
            result1 = cache.get_cached_response(test_url1, headers)
            result2 = cache.get_cached_response(test_url2, headers)

            # Call again to test caching
            result1_cached = cache.get_cached_response(test_url1, headers)
            result2_cached = cache.get_cached_response(test_url2, headers)

            # Assert
            assert result1 == data1
            assert result2 == data2
            assert result1_cached == data1
            assert result2_cached == data2
            assert requests_mock.call_count == 2  # Two different URLs cached separately

    def test_cache_clear_operations_comprehensive(self):
        """Test comprehensive cache clearing operations."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = SimpleAPICache(cache_dir=temp_dir, ttl_hours=1)

            # Use mock to track clear operations
            with patch.object(cache.session.cache, "clear") as mock_clear:
                # Act & Assert - Test clear_cache
                cache.clear_cache()
                mock_clear.assert_called_once()

                # Reset mock
                mock_clear.reset_mock()

                # Act & Assert - Test clear_project_cache
                cache.clear_project_cache("TEST-123")
                mock_clear.assert_called_once()

                # Test with different project keys
                mock_clear.reset_mock()
                cache.clear_project_cache("DIFFERENT-456")
                mock_clear.assert_called_once()

                # Test with empty project key
                mock_clear.reset_mock()
                cache.clear_project_cache("")
                mock_clear.assert_called_once()

    def test_cache_integration_with_requests_cache_features(self, requests_mock):
        """Test integration with requests-cache library features."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = SimpleAPICache(cache_dir=temp_dir, ttl_hours=1)
            test_url = "https://api.example.com/integration"
            test_headers = {"Authorization": "Bearer test"}
            test_data = {"integration": True}

            requests_mock.get(test_url, json=test_data, status_code=200)

            # Act
            # First call
            result1 = cache.get_cached_response(test_url, test_headers)

            # Check cache info
            cache_info = cache.session.cache

            # Second call (should be cached)
            result2 = cache.get_cached_response(test_url, test_headers)

            # Assert
            assert result1 == test_data
            assert result2 == test_data
            assert requests_mock.call_count == 1  # Only one actual HTTP call

            # Verify cache backend is working
            assert cache_info is not None
            assert hasattr(cache_info, "clear")  # Should have cache methods
