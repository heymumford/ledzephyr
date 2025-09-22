"""Simple error handling for ledzephyr."""

import logging
import time
from collections.abc import Callable
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Rate limit exceeded error."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class APIError(Exception):
    """Generic API error."""

    pass


class CircuitBreaker:
    """Simple circuit breaker to prevent hammering failed services."""

    def __init__(self, name: str, failure_threshold: int = 5, timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.is_open = False

    def call_succeeded(self):
        """Reset on success."""
        self.failure_count = 0
        self.is_open = False
        self.last_failure_time = None

    def call_failed(self):
        """Record failure and potentially open circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            logger.warning(
                f"Circuit breaker {self.name} opened after {self.failure_count} failures"
            )

    def can_attempt(self) -> bool:
        """Check if we can attempt a call."""
        if not self.is_open:
            return True

        # Check if timeout has passed
        if self.last_failure_time and (time.time() - self.last_failure_time) > self.timeout:
            self.is_open = False
            self.failure_count = 0
            logger.info(f"Circuit breaker {self.name} reset after timeout")
            return True

        return False


class ErrorHandler:
    """Simple error handler with circuit breakers."""

    def __init__(self):
        self.circuit_breakers = {}

    def register_circuit_breaker(self, name: str, **kwargs):
        """Register a circuit breaker."""
        self.circuit_breakers[name] = CircuitBreaker(name, **kwargs)

    def with_circuit_breaker(self, name: str):
        """Decorator to add circuit breaker to a function."""

        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs) -> Any:
                breaker = self.circuit_breakers.get(name)
                if not breaker:
                    return func(*args, **kwargs)

                if not breaker.can_attempt():
                    raise APIError(f"Circuit breaker {name} is open")

                try:
                    result = func(*args, **kwargs)
                    breaker.call_succeeded()
                    return result
                except Exception:
                    breaker.call_failed()
                    raise

            return wrapper

        return decorator


# Global instance
_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


# Simple retry decorator using tenacity
def retry_on_rate_limit(max_attempts: int = 3):
    """Retry decorator for rate limit errors."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=lambda e: isinstance(e, RateLimitError),
        before_sleep=lambda retry_state: logger.info(
            f"Rate limited, retrying in {retry_state.next_action.sleep} seconds..."
        ),
    )
