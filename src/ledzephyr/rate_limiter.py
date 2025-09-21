"""
Rate limiting and throttling for API requests.

Implements various rate limiting strategies including
token bucket, sliding window, and adaptive rate limiting.
"""

import asyncio
import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock, Semaphore

logger = logging.getLogger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""

    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    ADAPTIVE = "adaptive"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_second: float = 10.0
    burst_size: int = 20
    window_size: int = 60  # seconds
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    adaptive_min: float = 1.0
    adaptive_max: float = 100.0
    backoff_factor: float = 0.5
    increase_factor: float = 1.1


@dataclass
class RateLimitStatus:
    """Current status of rate limiter."""

    current_rate: float
    available_tokens: int
    next_reset: datetime
    total_requests: int = 0
    rejected_requests: int = 0
    current_window_requests: int = 0
    is_throttled: bool = False


class TokenBucket:
    """Token bucket rate limiter implementation."""

    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = Lock()

    def consume(self, tokens: int = 1) -> tuple[bool, float]:
        """
        Try to consume tokens from the bucket.

        Returns:
            Tuple of (success, wait_time_if_failed)
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now

            # Add tokens based on elapsed time
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0
            else:
                # Calculate wait time
                required_tokens = tokens - self.tokens
                wait_time = required_tokens / self.rate
                return False, wait_time

    def get_available_tokens(self) -> int:
        """Get current available tokens."""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            return min(self.capacity, int(self.tokens + elapsed * self.rate))


class SlidingWindow:
    """Sliding window rate limiter implementation."""

    def __init__(self, window_size: int, max_requests: int):
        self.window_size = window_size  # seconds
        self.max_requests = max_requests
        self.requests = deque()
        self.lock = Lock()

    def allow_request(self) -> tuple[bool, float]:
        """
        Check if request is allowed in current window.

        Returns:
            Tuple of (allowed, wait_time_if_not)
        """
        with self.lock:
            now = time.time()
            cutoff = now - self.window_size

            # Remove old requests outside window
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()

            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True, 0.0
            else:
                # Calculate wait time until oldest request expires
                oldest = self.requests[0]
                wait_time = oldest + self.window_size - now
                return False, wait_time

    def get_current_count(self) -> int:
        """Get current request count in window."""
        with self.lock:
            now = time.time()
            cutoff = now - self.window_size

            # Clean old requests
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()

            return len(self.requests)


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on response times and errors."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.current_rate = config.requests_per_second
        self.success_count = 0
        self.error_count = 0
        self.response_times: deque = deque(maxlen=100)
        self.last_adjustment = time.time()
        self.lock = Lock()

    def record_success(self, response_time: float):
        """Record successful request."""
        with self.lock:
            self.success_count += 1
            self.response_times.append(response_time)
            self._adjust_rate()

    def record_error(self, error_type: str):
        """Record failed request."""
        with self.lock:
            self.error_count += 1

            # Back off on rate limit errors
            if error_type == "rate_limit":
                self.current_rate *= self.config.backoff_factor
                self.current_rate = max(self.config.adaptive_min, self.current_rate)
                logger.info(f"Backing off rate to {self.current_rate:.2f} rps")

    def _adjust_rate(self):
        """Adjust rate based on performance metrics."""
        now = time.time()
        if now - self.last_adjustment < 10:  # Adjust every 10 seconds
            return

        self.last_adjustment = now

        if not self.response_times:
            return

        # Calculate metrics
        avg_response = sum(self.response_times) / len(self.response_times)
        error_rate = self.error_count / max(1, self.success_count + self.error_count)

        # Adjust rate based on performance
        if error_rate < 0.01 and avg_response < 0.5:
            # Good performance, increase rate
            self.current_rate *= self.config.increase_factor
            self.current_rate = min(self.config.adaptive_max, self.current_rate)
            logger.info(f"Increasing rate to {self.current_rate:.2f} rps")
        elif error_rate > 0.05 or avg_response > 2.0:
            # Poor performance, decrease rate
            self.current_rate *= self.config.backoff_factor
            self.current_rate = max(self.config.adaptive_min, self.current_rate)
            logger.info(f"Decreasing rate to {self.current_rate:.2f} rps")

        # Reset counters
        self.success_count = 0
        self.error_count = 0

    def get_current_rate(self) -> float:
        """Get current adaptive rate."""
        return self.current_rate


class RateLimiter:
    """Main rate limiter with multiple strategies."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.strategy = config.strategy
        self.total_requests = 0
        self.rejected_requests = 0

        # Initialize strategy-specific components
        if self.strategy == RateLimitStrategy.TOKEN_BUCKET:
            self.token_bucket = TokenBucket(config.requests_per_second, config.burst_size)
        elif self.strategy == RateLimitStrategy.SLIDING_WINDOW:
            self.sliding_window = SlidingWindow(
                config.window_size, int(config.requests_per_second * config.window_size)
            )
        elif self.strategy == RateLimitStrategy.ADAPTIVE:
            self.adaptive = AdaptiveRateLimiter(config)
            self.token_bucket = TokenBucket(config.requests_per_second, config.burst_size)

        # Semaphore for concurrent request limiting
        self.semaphore = Semaphore(config.burst_size)

    def acquire(self, timeout: float | None = None) -> bool:
        """
        Acquire permission to make a request.

        Args:
            timeout: Maximum time to wait for permission

        Returns:
            True if permission granted, False otherwise
        """
        self.total_requests += 1

        if self.strategy == RateLimitStrategy.TOKEN_BUCKET:
            allowed, wait_time = self.token_bucket.consume()
            if not allowed:
                if timeout and wait_time <= timeout:
                    time.sleep(wait_time)
                    allowed, _ = self.token_bucket.consume()
                else:
                    self.rejected_requests += 1
                    return False
            return allowed

        elif self.strategy == RateLimitStrategy.SLIDING_WINDOW:
            allowed, wait_time = self.sliding_window.allow_request()
            if not allowed:
                if timeout and wait_time <= timeout:
                    time.sleep(wait_time)
                    allowed, _ = self.sliding_window.allow_request()
                else:
                    self.rejected_requests += 1
                    return False
            return allowed

        elif self.strategy == RateLimitStrategy.ADAPTIVE:
            # Update token bucket with adaptive rate
            self.token_bucket.rate = self.adaptive.get_current_rate()
            return self.acquire(timeout)  # Recursive call with updated rate

        return True

    def release(self):
        """Release a request slot (for semaphore-based limiting)."""
        if hasattr(self, "semaphore"):
            self.semaphore.release()

    def record_response(self, success: bool, response_time: float = 0.0):
        """Record response for adaptive rate limiting."""
        if self.strategy == RateLimitStrategy.ADAPTIVE and hasattr(self, "adaptive"):
            if success:
                self.adaptive.record_success(response_time)
            else:
                self.adaptive.record_error("general")

    def get_status(self) -> RateLimitStatus:
        """Get current rate limiter status."""
        status = RateLimitStatus(
            current_rate=self.config.requests_per_second,
            available_tokens=0,
            next_reset=datetime.now() + timedelta(seconds=60),
            total_requests=self.total_requests,
            rejected_requests=self.rejected_requests,
        )

        if self.strategy == RateLimitStrategy.TOKEN_BUCKET:
            status.available_tokens = self.token_bucket.get_available_tokens()
        elif self.strategy == RateLimitStrategy.SLIDING_WINDOW:
            status.current_window_requests = self.sliding_window.get_current_count()
        elif self.strategy == RateLimitStrategy.ADAPTIVE:
            status.current_rate = self.adaptive.get_current_rate()
            status.available_tokens = self.token_bucket.get_available_tokens()

        status.is_throttled = status.available_tokens == 0

        return status

    def reset(self):
        """Reset rate limiter state."""
        self.total_requests = 0
        self.rejected_requests = 0

        if hasattr(self, "token_bucket"):
            self.token_bucket.tokens = self.token_bucket.capacity
        if hasattr(self, "sliding_window"):
            self.sliding_window.requests.clear()
        if hasattr(self, "adaptive"):
            self.adaptive.current_rate = self.config.requests_per_second
            self.adaptive.success_count = 0
            self.adaptive.error_count = 0


class MultiTenantRateLimiter:
    """Rate limiter supporting multiple tenants/endpoints."""

    def __init__(self, default_config: RateLimitConfig):
        self.default_config = default_config
        self.limiters: dict[str, RateLimiter] = {}
        self.lock = Lock()

    def get_limiter(self, key: str) -> RateLimiter:
        """Get or create rate limiter for a key."""
        with self.lock:
            if key not in self.limiters:
                self.limiters[key] = RateLimiter(self.default_config)
            return self.limiters[key]

    def acquire(self, key: str, timeout: float | None = None) -> bool:
        """Acquire permission for a specific key."""
        limiter = self.get_limiter(key)
        return limiter.acquire(timeout)

    def record_response(self, key: str, success: bool, response_time: float = 0.0):
        """Record response for a specific key."""
        limiter = self.get_limiter(key)
        limiter.record_response(success, response_time)

    def get_all_status(self) -> dict[str, RateLimitStatus]:
        """Get status for all limiters."""
        with self.lock:
            return {key: limiter.get_status() for key, limiter in self.limiters.items()}


# Decorator for rate limiting


def rate_limited(
    requests_per_second: float = 10.0,
    burst_size: int = 20,
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET,
    key_func: Callable | None = None,
):
    """
    Decorator for rate limiting function calls.

    Args:
        requests_per_second: Maximum request rate
        burst_size: Maximum burst capacity
        strategy: Rate limiting strategy to use
        key_func: Function to extract rate limit key from arguments
    """
    config = RateLimitConfig(
        requests_per_second=requests_per_second,
        burst_size=burst_size,
        strategy=strategy,
    )

    if key_func:
        limiter = MultiTenantRateLimiter(config)
    else:
        limiter = RateLimiter(config)

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()

            # Get rate limit key if applicable
            if key_func:
                key = key_func(*args, **kwargs)
                acquired = limiter.acquire(key, timeout=1.0)
            else:
                acquired = limiter.acquire(timeout=1.0)

            if not acquired:
                from ledzephyr.error_handler import RateLimitError

                raise RateLimitError(
                    f"Rate limit exceeded for {func.__name__}",
                    retry_after=1,
                )

            try:
                result = func(*args, **kwargs)
                response_time = time.time() - start_time

                if key_func:
                    limiter.record_response(key, True, response_time)
                else:
                    limiter.record_response(True, response_time)

                return result
            except Exception:
                response_time = time.time() - start_time

                if key_func:
                    key = key_func(*args, **kwargs)
                    limiter.record_response(key, False, response_time)
                else:
                    limiter.record_response(False, response_time)

                raise

        return wrapper

    return decorator


# Async rate limiting support


class AsyncRateLimiter:
    """Async rate limiter for asyncio applications."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.burst_size)
        self.token_bucket = TokenBucket(config.requests_per_second, config.burst_size)

    async def acquire(self):
        """Acquire permission asynchronously."""
        async with self.semaphore:
            while True:
                allowed, wait_time = self.token_bucket.consume()
                if allowed:
                    return True
                await asyncio.sleep(wait_time)

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
