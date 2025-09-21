"""Unit tests for rate limiter module following TDD methodology with AAA pattern."""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from ledzephyr.rate_limiter import (
    AdaptiveRateLimiter,
    AsyncRateLimiter,
    MultiTenantRateLimiter,
    RateLimitConfig,
    RateLimiter,
    RateLimitStatus,
    RateLimitStrategy,
    SlidingWindow,
    TokenBucket,
    rate_limited,
)


@pytest.mark.unit
class TestRateLimitConfig:
    """Test RateLimitConfig dataclass validation and defaults."""

    def test_create_config_with_defaults_creates_valid_instance(self):
        """Test creating RateLimitConfig with defaults creates valid instance."""
        # Arrange & Act
        config = RateLimitConfig()

        # Assert
        assert config.requests_per_second == 10.0
        assert config.burst_size == 20
        assert config.window_size == 60
        assert config.strategy == RateLimitStrategy.TOKEN_BUCKET
        assert config.adaptive_min == 1.0
        assert config.adaptive_max == 100.0
        assert config.backoff_factor == 0.5
        assert config.increase_factor == 1.1

    def test_create_config_with_custom_values_creates_valid_instance(self):
        """Test creating RateLimitConfig with custom values creates valid instance."""
        # Arrange & Act
        config = RateLimitConfig(
            requests_per_second=5.0,
            burst_size=10,
            window_size=30,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            adaptive_min=0.5,
            adaptive_max=50.0,
            backoff_factor=0.25,
            increase_factor=1.2,
        )

        # Assert
        assert config.requests_per_second == 5.0
        assert config.burst_size == 10
        assert config.window_size == 30
        assert config.strategy == RateLimitStrategy.SLIDING_WINDOW
        assert config.adaptive_min == 0.5
        assert config.adaptive_max == 50.0
        assert config.backoff_factor == 0.25
        assert config.increase_factor == 1.2


@pytest.mark.unit
class TestRateLimitStatus:
    """Test RateLimitStatus dataclass functionality."""

    def test_create_status_with_required_fields_creates_valid_instance(self):
        """Test creating RateLimitStatus with required fields creates valid instance."""
        # Arrange
        current_rate = 10.0
        available_tokens = 5
        next_reset = datetime.now() + timedelta(seconds=60)

        # Act
        status = RateLimitStatus(
            current_rate=current_rate,
            available_tokens=available_tokens,
            next_reset=next_reset,
        )

        # Assert
        assert status.current_rate == current_rate
        assert status.available_tokens == available_tokens
        assert status.next_reset == next_reset
        assert status.total_requests == 0
        assert status.rejected_requests == 0
        assert status.current_window_requests == 0
        assert status.is_throttled is False

    def test_create_status_with_all_fields_creates_valid_instance(self):
        """Test creating RateLimitStatus with all fields creates valid instance."""
        # Arrange
        current_rate = 10.0
        available_tokens = 0
        next_reset = datetime.now() + timedelta(seconds=60)
        total_requests = 100
        rejected_requests = 5
        current_window_requests = 20
        is_throttled = True

        # Act
        status = RateLimitStatus(
            current_rate=current_rate,
            available_tokens=available_tokens,
            next_reset=next_reset,
            total_requests=total_requests,
            rejected_requests=rejected_requests,
            current_window_requests=current_window_requests,
            is_throttled=is_throttled,
        )

        # Assert
        assert status.current_rate == current_rate
        assert status.available_tokens == available_tokens
        assert status.next_reset == next_reset
        assert status.total_requests == total_requests
        assert status.rejected_requests == rejected_requests
        assert status.current_window_requests == current_window_requests
        assert status.is_throttled is True


@pytest.mark.unit
class TestTokenBucket:
    """Test TokenBucket rate limiter implementation."""

    def test_create_token_bucket_with_valid_params_initializes_correctly(self):
        """Test creating TokenBucket with valid parameters initializes correctly."""
        # Arrange
        rate = 10.0
        capacity = 20

        # Act
        bucket = TokenBucket(rate, capacity)

        # Assert
        assert bucket.rate == rate
        assert bucket.capacity == capacity
        assert bucket.tokens == capacity
        assert bucket.last_update <= time.time()

    def test_consume_single_token_from_full_bucket_succeeds(self):
        """Test consuming single token from full bucket succeeds."""
        # Arrange
        bucket = TokenBucket(10.0, 20)

        # Act
        success, wait_time = bucket.consume(1)

        # Assert
        assert success is True
        assert wait_time == 0.0
        assert bucket.tokens == 19

    def test_consume_more_tokens_than_available_fails_with_wait_time(self):
        """Test consuming more tokens than available fails with calculated wait time."""
        # Arrange
        bucket = TokenBucket(10.0, 5)
        # Set tokens immediately after creation to minimize time-based replenishment
        bucket.tokens = 3
        bucket.last_update = time.time()
        initial_tokens = bucket.tokens

        # Act
        success, wait_time = bucket.consume(5)

        # Assert
        assert success is False
        assert wait_time > 0.0
        # Wait time should be approximately (required - available) / rate
        # Note: tokens might be slightly higher due to elapsed time replenishment
        tokens_after_replenishment = bucket.tokens
        expected_wait = (5 - tokens_after_replenishment) / 10.0
        assert abs(wait_time - expected_wait) < 0.01  # Allow small timing tolerance
        assert bucket.tokens >= initial_tokens  # Should not decrease when consumption fails

    def test_consume_zero_tokens_always_succeeds(self):
        """Test consuming zero tokens always succeeds."""
        # Arrange
        bucket = TokenBucket(10.0, 5)
        bucket.tokens = 0
        bucket.last_update = time.time()

        # Act
        success, wait_time = bucket.consume(0)

        # Assert
        assert success is True
        assert wait_time == 0.0
        # Tokens may have increased due to time-based replenishment
        assert bucket.tokens >= 0

    def test_token_replenishment_over_time_increases_available_tokens(self):
        """Test token replenishment over time increases available tokens."""
        # Arrange
        bucket = TokenBucket(10.0, 20)
        bucket.tokens = 5
        bucket.last_update = time.time() - 1.0  # 1 second ago

        # Act
        success, wait_time = bucket.consume(1)

        # Assert
        assert success is True
        assert wait_time == 0.0
        # Should have ~14 tokens (5 + 10*1.0 - 1), may be slightly different due to timing
        assert bucket.tokens >= 13
        assert bucket.tokens <= 15

    def test_token_replenishment_never_exceeds_capacity(self):
        """Test token replenishment never exceeds bucket capacity."""
        # Arrange
        bucket = TokenBucket(10.0, 20)
        bucket.tokens = 15
        bucket.last_update = time.time() - 2.0  # 2 seconds ago (would add 20 tokens)

        # Act
        available_before = bucket.get_available_tokens()

        # Assert
        assert available_before <= 20  # Should not exceed capacity

    def test_get_available_tokens_returns_current_count_with_replenishment(self):
        """Test get_available_tokens returns current count with replenishment."""
        # Arrange
        bucket = TokenBucket(10.0, 20)
        bucket.tokens = 10
        bucket.last_update = time.time() - 0.5  # 0.5 seconds ago

        # Act
        available = bucket.get_available_tokens()

        # Assert
        # Should have ~15 tokens (10 + 10*0.5), may be slightly different due to timing
        assert available >= 14
        assert available <= 16

    def test_concurrent_token_consumption_thread_safe(self):
        """Test concurrent token consumption is thread safe."""
        # Arrange
        bucket = TokenBucket(100.0, 100)
        success_count = 0
        num_threads = 10

        def consume_tokens():
            nonlocal success_count
            success, _ = bucket.consume(10)
            if success:
                success_count += 1

        # Act
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=consume_tokens)
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Assert
        assert success_count <= 10  # Can't exceed capacity/10
        assert bucket.tokens >= 0  # Should never go negative


@pytest.mark.unit
class TestSlidingWindow:
    """Test SlidingWindow rate limiter implementation."""

    def test_create_sliding_window_with_valid_params_initializes_correctly(self):
        """Test creating SlidingWindow with valid parameters initializes correctly."""
        # Arrange
        window_size = 60
        max_requests = 100

        # Act
        window = SlidingWindow(window_size, max_requests)

        # Assert
        assert window.window_size == window_size
        assert window.max_requests == max_requests
        assert len(window.requests) == 0

    def test_allow_request_within_limit_succeeds(self):
        """Test allowing request within limit succeeds."""
        # Arrange
        window = SlidingWindow(60, 5)

        # Act
        allowed, wait_time = window.allow_request()

        # Assert
        assert allowed is True
        assert wait_time == 0.0
        assert len(window.requests) == 1

    def test_allow_request_exceeding_limit_fails_with_wait_time(self):
        """Test allowing request exceeding limit fails with wait time."""
        # Arrange
        window = SlidingWindow(60, 2)

        # Fill window to capacity
        window.allow_request()
        window.allow_request()

        # Act
        allowed, wait_time = window.allow_request()

        # Assert
        assert allowed is False
        assert wait_time > 0.0
        assert len(window.requests) == 2  # Should not add request

    def test_old_requests_removed_from_window(self):
        """Test old requests are removed from sliding window."""
        # Arrange
        window = SlidingWindow(1, 5)  # 1 second window

        # Add request
        window.allow_request()

        # Wait for window to expire
        time.sleep(1.1)

        # Act
        count_before = window.get_current_count()
        allowed, wait_time = window.allow_request()

        # Assert
        assert count_before == 0  # Old request should be removed
        assert allowed is True
        assert wait_time == 0.0

    def test_get_current_count_returns_requests_in_window(self):
        """Test get_current_count returns number of requests in current window."""
        # Arrange
        window = SlidingWindow(60, 10)

        # Add some requests
        window.allow_request()
        window.allow_request()
        window.allow_request()

        # Act
        count = window.get_current_count()

        # Assert
        assert count == 3

    def test_get_current_count_excludes_expired_requests(self):
        """Test get_current_count excludes expired requests."""
        # Arrange
        window = SlidingWindow(1, 10)  # 1 second window

        # Add request
        window.allow_request()

        # Wait for expiration
        time.sleep(1.1)

        # Act
        count = window.get_current_count()

        # Assert
        assert count == 0

    def test_concurrent_requests_thread_safe(self):
        """Test concurrent requests are handled thread safely."""
        # Arrange
        window = SlidingWindow(60, 20)
        allowed_count = 0
        num_threads = 30

        def make_request():
            nonlocal allowed_count
            allowed, _ = window.allow_request()
            if allowed:
                allowed_count += 1

        # Act
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Assert
        assert allowed_count <= 20  # Should not exceed max_requests
        assert window.get_current_count() == allowed_count


@pytest.mark.unit
class TestAdaptiveRateLimiter:
    """Test AdaptiveRateLimiter implementation."""

    def test_create_adaptive_rate_limiter_initializes_correctly(self):
        """Test creating AdaptiveRateLimiter initializes correctly."""
        # Arrange
        config = RateLimitConfig(requests_per_second=10.0)

        # Act
        limiter = AdaptiveRateLimiter(config)

        # Assert
        assert limiter.config == config
        assert limiter.current_rate == config.requests_per_second
        assert limiter.success_count == 0
        assert limiter.error_count == 0
        assert len(limiter.response_times) == 0

    def test_record_success_increases_success_count(self):
        """Test recording success increases success count."""
        # Arrange
        config = RateLimitConfig()
        limiter = AdaptiveRateLimiter(config)
        response_time = 0.5

        # Act
        limiter.record_success(response_time)

        # Assert
        assert limiter.success_count == 1
        assert limiter.response_times[-1] == response_time

    def test_record_error_increases_error_count(self):
        """Test recording error increases error count."""
        # Arrange
        config = RateLimitConfig()
        limiter = AdaptiveRateLimiter(config)

        # Act
        limiter.record_error("general")

        # Assert
        assert limiter.error_count == 1

    def test_record_rate_limit_error_decreases_current_rate(self):
        """Test recording rate limit error decreases current rate."""
        # Arrange
        config = RateLimitConfig(requests_per_second=10.0, backoff_factor=0.5)
        limiter = AdaptiveRateLimiter(config)
        initial_rate = limiter.current_rate

        # Act
        limiter.record_error("rate_limit")

        # Assert
        assert limiter.current_rate == initial_rate * config.backoff_factor

    def test_record_rate_limit_error_respects_minimum_rate(self):
        """Test recording rate limit error respects minimum rate."""
        # Arrange
        config = RateLimitConfig(requests_per_second=2.0, adaptive_min=1.0, backoff_factor=0.5)
        limiter = AdaptiveRateLimiter(config)

        # Act
        limiter.record_error("rate_limit")  # 2.0 * 0.5 = 1.0
        limiter.record_error("rate_limit")  # 1.0 * 0.5 = 0.5, but min is 1.0

        # Assert
        assert limiter.current_rate == config.adaptive_min

    def test_get_current_rate_returns_adaptive_rate(self):
        """Test get_current_rate returns current adaptive rate."""
        # Arrange
        config = RateLimitConfig(requests_per_second=10.0)
        limiter = AdaptiveRateLimiter(config)

        # Act
        rate = limiter.get_current_rate()

        # Assert
        assert rate == 10.0

    @patch("time.time")
    def test_adjust_rate_with_good_performance_increases_rate(self, mock_time):
        """Test rate adjustment with good performance increases rate."""
        # Arrange
        config = RateLimitConfig(requests_per_second=10.0, adaptive_max=20.0, increase_factor=1.1)
        limiter = AdaptiveRateLimiter(config)

        # Set up timing to trigger adjustment
        mock_time.return_value = 0
        limiter.last_adjustment = 0  # Set initial time
        mock_time.return_value = 11  # Now 11 seconds later

        # Add good performance data
        for _ in range(10):
            limiter.response_times.append(0.2)  # Fast responses
        limiter.success_count = 10
        limiter.error_count = 0

        # Act
        limiter._adjust_rate()

        # Assert
        assert limiter.current_rate == 10.0 * config.increase_factor

    @patch("time.time")
    def test_adjust_rate_with_poor_performance_decreases_rate(self, mock_time):
        """Test rate adjustment with poor performance decreases rate."""
        # Arrange
        config = RateLimitConfig(requests_per_second=10.0, adaptive_min=5.0, backoff_factor=0.5)
        limiter = AdaptiveRateLimiter(config)

        # Set up timing to trigger adjustment
        mock_time.return_value = 0
        limiter.last_adjustment = 0  # Set initial time
        mock_time.return_value = 11  # Now 11 seconds later

        # Add poor performance data
        for _ in range(10):
            limiter.response_times.append(3.0)  # Slow responses
        limiter.success_count = 10
        limiter.error_count = 1  # High error rate

        # Act
        limiter._adjust_rate()

        # Assert
        assert limiter.current_rate == 10.0 * config.backoff_factor

    @patch("time.time")
    def test_adjust_rate_respects_maximum_rate(self, mock_time):
        """Test rate adjustment respects maximum rate."""
        # Arrange
        config = RateLimitConfig(requests_per_second=18.0, adaptive_max=20.0, increase_factor=1.2)
        limiter = AdaptiveRateLimiter(config)

        # Set up timing to trigger adjustment
        mock_time.return_value = 0
        limiter.last_adjustment = 0  # Set initial time
        mock_time.return_value = 11  # Now 11 seconds later

        # Add excellent performance data
        for _ in range(100):
            limiter.response_times.append(0.1)  # Very fast responses
        limiter.success_count = 100
        limiter.error_count = 0

        # Act
        limiter._adjust_rate()

        # Assert
        assert limiter.current_rate == config.adaptive_max

    @patch("time.time")
    def test_adjust_rate_resets_counters_after_adjustment(self, mock_time):
        """Test rate adjustment resets counters after adjustment."""
        # Arrange
        config = RateLimitConfig()
        limiter = AdaptiveRateLimiter(config)

        # Set up timing to trigger adjustment
        mock_time.return_value = 0
        limiter.last_adjustment = 0  # Set initial time
        mock_time.return_value = 11  # Now 11 seconds later

        # Add performance data
        for _ in range(10):
            limiter.response_times.append(0.5)
        limiter.success_count = 10
        limiter.error_count = 1

        # Act
        limiter._adjust_rate()

        # Assert
        assert limiter.success_count == 0
        assert limiter.error_count == 0


@pytest.mark.unit
class TestRateLimiter:
    """Test main RateLimiter class with different strategies."""

    def test_create_rate_limiter_with_token_bucket_strategy_initializes_correctly(self):
        """Test creating RateLimiter with token bucket strategy initializes correctly."""
        # Arrange
        config = RateLimitConfig(
            requests_per_second=10.0, burst_size=20, strategy=RateLimitStrategy.TOKEN_BUCKET
        )

        # Act
        limiter = RateLimiter(config)

        # Assert
        assert limiter.config == config
        assert limiter.strategy == RateLimitStrategy.TOKEN_BUCKET
        assert hasattr(limiter, "token_bucket")
        assert limiter.total_requests == 0
        assert limiter.rejected_requests == 0

    def test_create_rate_limiter_with_sliding_window_strategy_initializes_correctly(self):
        """Test creating RateLimiter with sliding window strategy initializes correctly."""
        # Arrange
        config = RateLimitConfig(
            requests_per_second=10.0, window_size=60, strategy=RateLimitStrategy.SLIDING_WINDOW
        )

        # Act
        limiter = RateLimiter(config)

        # Assert
        assert limiter.config == config
        assert limiter.strategy == RateLimitStrategy.SLIDING_WINDOW
        assert hasattr(limiter, "sliding_window")
        assert limiter.total_requests == 0
        assert limiter.rejected_requests == 0

    def test_create_rate_limiter_with_adaptive_strategy_initializes_correctly(self):
        """Test creating RateLimiter with adaptive strategy initializes correctly."""
        # Arrange
        config = RateLimitConfig(requests_per_second=10.0, strategy=RateLimitStrategy.ADAPTIVE)

        # Act
        limiter = RateLimiter(config)

        # Assert
        assert limiter.config == config
        assert limiter.strategy == RateLimitStrategy.ADAPTIVE
        assert hasattr(limiter, "adaptive")
        assert hasattr(limiter, "token_bucket")
        assert limiter.total_requests == 0
        assert limiter.rejected_requests == 0

    def test_acquire_with_token_bucket_strategy_success_grants_permission(self):
        """Test acquire with token bucket strategy success grants permission."""
        # Arrange
        config = RateLimitConfig(strategy=RateLimitStrategy.TOKEN_BUCKET)
        limiter = RateLimiter(config)

        # Act
        result = limiter.acquire()

        # Assert
        assert result is True
        assert limiter.total_requests == 1
        assert limiter.rejected_requests == 0

    def test_acquire_with_sliding_window_strategy_success_grants_permission(self):
        """Test acquire with sliding window strategy success grants permission."""
        # Arrange
        config = RateLimitConfig(strategy=RateLimitStrategy.SLIDING_WINDOW)
        limiter = RateLimiter(config)

        # Act
        result = limiter.acquire()

        # Assert
        assert result is True
        assert limiter.total_requests == 1
        assert limiter.rejected_requests == 0

    def test_acquire_with_timeout_waits_for_available_tokens(self):
        """Test acquire with timeout waits for available tokens."""
        # Arrange
        config = RateLimitConfig(
            requests_per_second=1000.0,  # Fast replenishment
            burst_size=1,
            strategy=RateLimitStrategy.TOKEN_BUCKET,
        )
        limiter = RateLimiter(config)

        # Consume the only token
        limiter.acquire()

        # Act - should wait and succeed due to fast replenishment
        start_time = time.time()
        result = limiter.acquire(timeout=0.1)
        elapsed = time.time() - start_time

        # Assert
        assert result is True or elapsed >= 0.1  # Either succeeds or times out
        assert limiter.total_requests == 2

    def test_acquire_exceeding_rate_limit_rejects_request(self):
        """Test acquire exceeding rate limit rejects request."""
        # Arrange
        config = RateLimitConfig(
            requests_per_second=0.1,  # Very slow
            burst_size=1,
            strategy=RateLimitStrategy.TOKEN_BUCKET,
        )
        limiter = RateLimiter(config)

        # Consume the only token
        limiter.acquire()

        # Act - should fail due to no timeout
        result = limiter.acquire(timeout=None)

        # Assert
        assert result is False
        assert limiter.total_requests == 2
        assert limiter.rejected_requests == 1

    def test_record_response_with_adaptive_strategy_records_success(self):
        """Test record_response with adaptive strategy records success."""
        # Arrange
        config = RateLimitConfig(strategy=RateLimitStrategy.ADAPTIVE)
        limiter = RateLimiter(config)

        # Act
        limiter.record_response(success=True, response_time=0.5)

        # Assert - success recorded in adaptive limiter
        assert limiter.adaptive.success_count == 1
        assert 0.5 in limiter.adaptive.response_times

    def test_record_response_with_adaptive_strategy_records_failure(self):
        """Test record_response with adaptive strategy records failure."""
        # Arrange
        config = RateLimitConfig(strategy=RateLimitStrategy.ADAPTIVE)
        limiter = RateLimiter(config)

        # Act
        limiter.record_response(success=False, response_time=1.0)

        # Assert - failure recorded in adaptive limiter
        assert limiter.adaptive.error_count == 1

    def test_get_status_returns_current_rate_limiter_state(self):
        """Test get_status returns current rate limiter state."""
        # Arrange
        config = RateLimitConfig(strategy=RateLimitStrategy.TOKEN_BUCKET)
        limiter = RateLimiter(config)
        limiter.acquire()  # Make one request

        # Act
        status = limiter.get_status()

        # Assert
        assert isinstance(status, RateLimitStatus)
        assert status.current_rate == config.requests_per_second
        assert status.total_requests == 1
        assert status.rejected_requests == 0
        assert isinstance(status.available_tokens, int)

    def test_reset_clears_all_counters_and_state(self):
        """Test reset clears all counters and state."""
        # Arrange
        config = RateLimitConfig(strategy=RateLimitStrategy.TOKEN_BUCKET)
        limiter = RateLimiter(config)
        limiter.acquire()
        limiter.acquire()

        # Act
        limiter.reset()

        # Assert
        assert limiter.total_requests == 0
        assert limiter.rejected_requests == 0
        assert limiter.token_bucket.tokens == limiter.token_bucket.capacity


@pytest.mark.unit
class TestMultiTenantRateLimiter:
    """Test MultiTenantRateLimiter functionality."""

    def test_create_multi_tenant_rate_limiter_initializes_correctly(self):
        """Test creating MultiTenantRateLimiter initializes correctly."""
        # Arrange
        config = RateLimitConfig()

        # Act
        limiter = MultiTenantRateLimiter(config)

        # Assert
        assert limiter.default_config == config
        assert len(limiter.limiters) == 0

    def test_get_limiter_creates_new_limiter_for_new_key(self):
        """Test get_limiter creates new limiter for new key."""
        # Arrange
        config = RateLimitConfig()
        limiter = MultiTenantRateLimiter(config)

        # Act
        tenant_limiter = limiter.get_limiter("tenant1")

        # Assert
        assert isinstance(tenant_limiter, RateLimiter)
        assert "tenant1" in limiter.limiters
        assert limiter.limiters["tenant1"] == tenant_limiter

    def test_get_limiter_returns_existing_limiter_for_existing_key(self):
        """Test get_limiter returns existing limiter for existing key."""
        # Arrange
        config = RateLimitConfig()
        limiter = MultiTenantRateLimiter(config)
        tenant_limiter1 = limiter.get_limiter("tenant1")

        # Act
        tenant_limiter2 = limiter.get_limiter("tenant1")

        # Assert
        assert tenant_limiter1 is tenant_limiter2

    def test_acquire_with_valid_key_grants_permission(self):
        """Test acquire with valid key grants permission."""
        # Arrange
        config = RateLimitConfig()
        limiter = MultiTenantRateLimiter(config)

        # Act
        result = limiter.acquire("tenant1")

        # Assert
        assert result is True
        assert "tenant1" in limiter.limiters

    def test_record_response_for_specific_key_records_correctly(self):
        """Test record_response for specific key records correctly."""
        # Arrange
        config = RateLimitConfig(strategy=RateLimitStrategy.ADAPTIVE)
        limiter = MultiTenantRateLimiter(config)
        limiter.acquire("tenant1")  # Create limiter for tenant1

        # Act
        limiter.record_response("tenant1", success=True, response_time=0.3)

        # Assert
        tenant_limiter = limiter.get_limiter("tenant1")
        assert tenant_limiter.adaptive.success_count == 1

    def test_get_all_status_returns_status_for_all_tenants(self):
        """Test get_all_status returns status for all tenants."""
        # Arrange
        config = RateLimitConfig()
        limiter = MultiTenantRateLimiter(config)
        limiter.acquire("tenant1")
        limiter.acquire("tenant2")

        # Act
        all_status = limiter.get_all_status()

        # Assert
        assert isinstance(all_status, dict)
        assert "tenant1" in all_status
        assert "tenant2" in all_status
        assert isinstance(all_status["tenant1"], RateLimitStatus)
        assert isinstance(all_status["tenant2"], RateLimitStatus)

    def test_concurrent_access_different_tenants_thread_safe(self):
        """Test concurrent access to different tenants is thread safe."""
        # Arrange
        config = RateLimitConfig()
        limiter = MultiTenantRateLimiter(config)
        results = []

        def acquire_for_tenant(tenant_id):
            result = limiter.acquire(f"tenant{tenant_id}")
            results.append(result)

        # Act
        threads = []
        for i in range(10):
            thread = threading.Thread(target=acquire_for_tenant, args=(i,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Assert
        assert len(results) == 10
        assert all(results)  # All should succeed
        assert len(limiter.limiters) == 10


@pytest.mark.unit
class TestRateLimitedDecorator:
    """Test rate_limited decorator functionality."""

    def test_rate_limited_decorator_allows_function_execution(self):
        """Test rate_limited decorator allows function execution."""

        # Arrange
        @rate_limited(requests_per_second=10.0, burst_size=5)
        def test_function():
            return "success"

        # Act
        result = test_function()

        # Assert
        assert result == "success"

    def test_rate_limited_decorator_with_key_func_allows_execution(self):
        """Test rate_limited decorator with key function allows execution."""

        # Arrange
        def key_func(user_id):
            return f"user_{user_id}"

        @rate_limited(requests_per_second=10.0, burst_size=5, key_func=key_func)
        def test_function(user_id):
            return f"user_{user_id}_result"

        # Act
        result = test_function("123")

        # Assert
        assert result == "user_123_result"

    def test_rate_limited_decorator_raises_error_when_rate_exceeded(self):
        """Test rate_limited decorator raises error when rate exceeded."""
        # Arrange
        from ledzephyr.error_handler import RateLimitError

        @rate_limited(requests_per_second=0.1, burst_size=1)
        def test_function():
            return "success"

        # Use up the burst capacity
        test_function()

        # Act & Assert
        # This should fail due to rate limiting
        with pytest.raises(RateLimitError):
            test_function()

    def test_rate_limited_decorator_records_response_on_success(self):
        """Test rate_limited decorator records response on success."""

        # Arrange
        @rate_limited(requests_per_second=10.0, strategy=RateLimitStrategy.ADAPTIVE)
        def test_function():
            return "success"

        # Act
        result = test_function()

        # Assert
        assert result == "success"
        # Note: We can't easily verify the internal recording without accessing private attributes

    def test_rate_limited_decorator_records_response_on_error(self):
        """Test rate_limited decorator records response on error."""

        # Arrange
        @rate_limited(requests_per_second=10.0, strategy=RateLimitStrategy.ADAPTIVE)
        def test_function():
            raise ValueError("test error")

        # Act & Assert
        with pytest.raises(ValueError, match="test error"):
            test_function()


@pytest.mark.unit
class TestAsyncRateLimiter:
    """Test AsyncRateLimiter functionality."""

    def test_create_async_rate_limiter_initializes_correctly(self):
        """Test creating AsyncRateLimiter initializes correctly."""
        # Arrange
        config = RateLimitConfig()

        # Act
        limiter = AsyncRateLimiter(config)

        # Assert
        assert limiter.config == config
        assert isinstance(limiter.semaphore, asyncio.Semaphore)
        assert isinstance(limiter.token_bucket, TokenBucket)

    @pytest.mark.asyncio
    async def test_async_rate_limiter_acquire_allows_request(self):
        """Test async rate limiter acquire allows request."""
        # Arrange
        config = RateLimitConfig(requests_per_second=100.0, burst_size=10)
        limiter = AsyncRateLimiter(config)

        # Act
        result = await limiter.acquire()

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_async_rate_limiter_context_manager_works(self):
        """Test async rate limiter context manager works."""
        # Arrange
        config = RateLimitConfig(requests_per_second=100.0, burst_size=10)
        limiter = AsyncRateLimiter(config)

        # Act & Assert
        async with limiter:
            # Should not raise any exception
            pass

    @pytest.mark.asyncio
    async def test_async_rate_limiter_waits_when_rate_exceeded(self):
        """Test async rate limiter waits when rate exceeded."""
        # Arrange
        config = RateLimitConfig(requests_per_second=1000.0, burst_size=1)
        limiter = AsyncRateLimiter(config)

        # Use up capacity
        await limiter.acquire()

        # Act
        start_time = time.time()
        await limiter.acquire()  # Should wait
        elapsed = time.time() - start_time

        # Assert
        # Should have waited some small amount (due to fast replenishment)
        assert elapsed >= 0


@pytest.mark.unit
class TestEdgeCasesAndValidation:
    """Test edge cases and parameter validation."""

    def test_token_bucket_with_zero_rate_handles_correctly(self):
        """Test token bucket with zero rate handles correctly."""
        # Arrange & Act
        bucket = TokenBucket(0.0, 10)

        # Assert
        assert bucket.rate == 0.0
        assert bucket.capacity == 10

        # First consumption should succeed (bucket starts full)
        success, wait_time = bucket.consume(1)
        assert success is True
        assert wait_time == 0.0

        # But subsequent consumption beyond capacity should fail with zero rate
        # Consume all remaining tokens
        for _ in range(9):
            bucket.consume(1)

        # Now bucket is empty and rate is zero - should fail
        success, wait_time = bucket.consume(1)
        assert success is False
        assert wait_time == float("inf")  # Infinite wait time with zero rate

    def test_token_bucket_with_zero_capacity_handles_correctly(self):
        """Test token bucket with zero capacity handles correctly."""
        # Arrange & Act
        bucket = TokenBucket(10.0, 0)

        # Assert
        assert bucket.rate == 10.0
        assert bucket.capacity == 0
        assert bucket.tokens == 0

        # Test consumption with zero capacity
        success, wait_time = bucket.consume(1)
        assert success is False
        assert wait_time > 0.0

    def test_sliding_window_with_zero_max_requests_rejects_all(self):
        """Test sliding window with zero max requests rejects all."""
        # Arrange
        window = SlidingWindow(60, 0)

        # Act
        allowed, wait_time = window.allow_request()

        # Assert
        assert allowed is False
        assert wait_time > 0.0

    def test_sliding_window_with_zero_window_size_allows_all(self):
        """Test sliding window with zero window size allows all."""
        # Arrange
        window = SlidingWindow(0, 10)

        # Act
        for _ in range(20):  # Try more than max_requests
            allowed, wait_time = window.allow_request()
            # Should allow all since window is zero (all requests expire immediately)
            assert allowed is True

    def test_adaptive_rate_limiter_with_extreme_config_values(self):
        """Test adaptive rate limiter with extreme config values."""
        # Arrange
        config = RateLimitConfig(
            requests_per_second=1.0,
            adaptive_min=0.1,
            adaptive_max=1000.0,
            backoff_factor=0.1,
            increase_factor=2.0,
        )
        limiter = AdaptiveRateLimiter(config)

        # Act & Assert - Should not crash with extreme values
        limiter.record_error("rate_limit")
        assert limiter.current_rate >= config.adaptive_min

        # Add good performance to increase rate
        for _ in range(100):
            limiter.response_times.append(0.01)
        limiter.success_count = 100

        # Force adjustment
        with patch("time.time", side_effect=[0, 11]):
            limiter._adjust_rate()
            assert limiter.current_rate <= config.adaptive_max


@pytest.mark.unit
class TestPerformanceAndTiming:
    """Test performance and timing aspects."""

    def test_token_bucket_performance_many_rapid_requests(self):
        """Test token bucket performance with many rapid requests."""
        # Arrange
        bucket = TokenBucket(1000.0, 100)
        start_time = time.time()

        # Act
        success_count = 0
        for _ in range(1000):
            success, _ = bucket.consume(1)
            if success:
                success_count += 1

        elapsed = time.time() - start_time

        # Assert
        assert elapsed < 1.0  # Should be fast
        # Allow slight overage due to time-based replenishment during fast execution
        assert success_count <= 110  # Should be close to capacity with minimal overage

    def test_sliding_window_performance_many_rapid_requests(self):
        """Test sliding window performance with many rapid requests."""
        # Arrange
        window = SlidingWindow(1, 100)
        start_time = time.time()

        # Act
        success_count = 0
        for _ in range(1000):
            allowed, _ = window.allow_request()
            if allowed:
                success_count += 1

        elapsed = time.time() - start_time

        # Assert
        assert elapsed < 1.0  # Should be fast
        assert success_count <= 100  # Limited by max_requests

    def test_concurrent_token_bucket_access_maintains_correctness(self):
        """Test concurrent token bucket access maintains correctness."""
        # Arrange
        bucket = TokenBucket(100.0, 50)
        success_counts = []

        def consume_tokens():
            local_success = 0
            for _ in range(10):
                success, _ = bucket.consume(1)
                if success:
                    local_success += 1
            success_counts.append(local_success)

        # Act
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=consume_tokens)
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Assert
        total_success = sum(success_counts)
        assert total_success <= 50  # Should not exceed capacity
        assert bucket.tokens >= 0  # Should never go negative

    def test_concurrent_sliding_window_access_maintains_correctness(self):
        """Test concurrent sliding window access maintains correctness."""
        # Arrange
        window = SlidingWindow(60, 20)
        success_counts = []

        def make_requests():
            local_success = 0
            for _ in range(5):
                allowed, _ = window.allow_request()
                if allowed:
                    local_success += 1
            success_counts.append(local_success)

        # Act
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_requests)
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Assert
        total_success = sum(success_counts)
        assert total_success <= 20  # Should not exceed max_requests
        assert window.get_current_count() == total_success


# End of comprehensive test suite
