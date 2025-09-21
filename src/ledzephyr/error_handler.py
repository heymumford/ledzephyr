"""
Comprehensive error handling and recovery for ledzephyr.

Provides centralized error management, recovery strategies,
and graceful degradation for the application.
"""

import functools
import logging
import traceback
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"  # Log and continue
    MEDIUM = "medium"  # Retry with backoff
    HIGH = "high"  # Alert and fallback
    CRITICAL = "critical"  # Fail fast with proper cleanup


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types."""

    RETRY = "retry"  # Retry with exponential backoff
    FALLBACK = "fallback"  # Use fallback value/behavior
    CIRCUIT_BREAK = "circuit_break"  # Stop attempting for a period
    DEGRADE = "degrade"  # Provide degraded service
    FAIL_FAST = "fail_fast"  # Fail immediately


@dataclass
class ErrorContext:
    """Context information for error handling."""

    error_type: type[Exception]
    error_message: str
    severity: ErrorSeverity
    timestamp: datetime = field(default_factory=datetime.now)
    operation: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)
    stack_trace: str | None = None


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""

    success: bool
    strategy_used: RecoveryStrategy
    value: Any = None
    error: Exception | None = None
    degraded: bool = False
    message: str | None = None


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = Exception,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise Exception(f"Circuit breaker {self.name} is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return False
        return datetime.now() > self.last_failure_time + timedelta(seconds=self.recovery_timeout)

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = "closed"
        logger.info(f"Circuit breaker {self.name} reset to closed")

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker {self.name} opened after {self.failure_count} failures"
            )
        elif self.state == "half-open":
            self.state = "open"
            logger.warning(f"Circuit breaker {self.name} reopened during half-open state")


class ErrorHandler:
    """Centralized error handling and recovery manager."""

    def __init__(self):
        self.error_history: list[ErrorContext] = []
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.fallback_values: dict[str, Any] = {}
        self.recovery_strategies: dict[type[Exception], RecoveryStrategy] = {
            ConnectionError: RecoveryStrategy.RETRY,
            TimeoutError: RecoveryStrategy.CIRCUIT_BREAK,
            ValueError: RecoveryStrategy.FALLBACK,
            KeyError: RecoveryStrategy.DEGRADE,
            PermissionError: RecoveryStrategy.FAIL_FAST,
        }

    def register_circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ) -> CircuitBreaker:
        """Register a new circuit breaker."""
        breaker = CircuitBreaker(name, failure_threshold, recovery_timeout)
        self.circuit_breakers[name] = breaker
        return breaker

    def register_fallback(self, key: str, value: Any):
        """Register a fallback value for a given key."""
        self.fallback_values[key] = value

    def handle_error(
        self,
        error: Exception,
        operation: str | None = None,
        severity: ErrorSeverity | None = None,
        **metadata,
    ) -> RecoveryResult:
        """Handle an error with appropriate recovery strategy."""
        # Determine severity if not provided
        if severity is None:
            severity = self._determine_severity(error)

        # Create error context
        context = ErrorContext(
            error_type=type(error),
            error_message=str(error),
            severity=severity,
            operation=operation,
            metadata=metadata,
            stack_trace=traceback.format_exc(),
        )

        # Log error
        self._log_error(context)

        # Store in history
        self.error_history.append(context)

        # Determine recovery strategy
        strategy = self.recovery_strategies.get(type(error), RecoveryStrategy.RETRY)

        # Execute recovery
        return self._execute_recovery(context, strategy)

    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity based on type and context."""
        if isinstance(error, PermissionError | AuthenticationError):
            return ErrorSeverity.CRITICAL
        elif isinstance(error, ConnectionError | TimeoutError):
            return ErrorSeverity.HIGH
        elif isinstance(error, ValueError | KeyError):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

    def _log_error(self, context: ErrorContext):
        """Log error based on severity."""
        log_message = (
            f"Error in {context.operation or 'unknown operation'}: " f"{context.error_message}"
        )

        if context.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra=context.metadata)
        elif context.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra=context.metadata)
        elif context.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra=context.metadata)
        else:
            logger.info(log_message, extra=context.metadata)

    def _execute_recovery(
        self,
        context: ErrorContext,
        strategy: RecoveryStrategy,
    ) -> RecoveryResult:
        """Execute recovery strategy."""
        if strategy == RecoveryStrategy.RETRY:
            return self._retry_recovery(context)
        elif strategy == RecoveryStrategy.FALLBACK:
            return self._fallback_recovery(context)
        elif strategy == RecoveryStrategy.CIRCUIT_BREAK:
            return self._circuit_break_recovery(context)
        elif strategy == RecoveryStrategy.DEGRADE:
            return self._degrade_recovery(context)
        else:  # FAIL_FAST
            return RecoveryResult(
                success=False,
                strategy_used=strategy,
                error=Exception(context.error_message),
            )

    def _retry_recovery(self, context: ErrorContext) -> RecoveryResult:
        """Attempt retry recovery."""
        if context.retry_count < context.max_retries:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.RETRY,
                message=f"Retry {context.retry_count + 1}/{context.max_retries}",
            )
        else:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.RETRY,
                error=Exception("Max retries exceeded"),
            )

    def _fallback_recovery(self, context: ErrorContext) -> RecoveryResult:
        """Use fallback value."""
        fallback_key = context.operation or "default"
        if fallback_key in self.fallback_values:
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.FALLBACK,
                value=self.fallback_values[fallback_key],
                degraded=True,
                message="Using fallback value",
            )
        else:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FALLBACK,
                error=Exception("No fallback available"),
            )

    def _circuit_break_recovery(self, context: ErrorContext) -> RecoveryResult:
        """Apply circuit breaker."""
        breaker_name = context.operation or "default"
        if breaker_name not in self.circuit_breakers:
            self.register_circuit_breaker(breaker_name)

        breaker = self.circuit_breakers[breaker_name]
        if breaker.state == "open":
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.CIRCUIT_BREAK,
                error=Exception(f"Circuit breaker {breaker_name} is open"),
            )
        else:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.CIRCUIT_BREAK,
                message="Circuit breaker allowing retry",
            )

    def _degrade_recovery(self, context: ErrorContext) -> RecoveryResult:
        """Provide degraded service."""
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.DEGRADE,
            value=None,
            degraded=True,
            message="Service degraded but operational",
        )

    @contextmanager
    def error_context(
        self,
        operation: str,
        fallback_value: Any = None,
        reraise: bool = True,
    ):
        """Context manager for error handling."""
        if fallback_value is not None:
            self.register_fallback(operation, fallback_value)

        try:
            yield
        except Exception as e:
            result = self.handle_error(e, operation=operation)

            if result.success:
                return result.value
            elif reraise:
                raise
            else:
                return fallback_value

    def get_error_stats(self) -> dict[str, Any]:
        """Get error statistics."""
        if not self.error_history:
            return {"total_errors": 0}

        stats = {
            "total_errors": len(self.error_history),
            "errors_by_severity": {},
            "errors_by_type": {},
            "recent_errors": [],
            "circuit_breakers": {},
        }

        # Count by severity
        for severity in ErrorSeverity:
            count = sum(1 for e in self.error_history if e.severity == severity)
            stats["errors_by_severity"][severity.value] = count

        # Count by type
        for error in self.error_history:
            error_type = error.error_type.__name__
            stats["errors_by_type"][error_type] = stats["errors_by_type"].get(error_type, 0) + 1

        # Recent errors
        stats["recent_errors"] = [
            {
                "timestamp": e.timestamp.isoformat(),
                "operation": e.operation,
                "error": e.error_message,
                "severity": e.severity.value,
            }
            for e in self.error_history[-10:]
        ]

        # Circuit breaker states
        for name, breaker in self.circuit_breakers.items():
            stats["circuit_breakers"][name] = {
                "state": breaker.state,
                "failure_count": breaker.failure_count,
            }

        return stats


# Decorators for common error handling patterns


def with_retry(
    max_attempts: int = 3,
    wait_strategy=None,
    retry_on: tuple = (ConnectionError, TimeoutError),
):
    """Decorator for automatic retry with exponential backoff."""
    if wait_strategy is None:
        wait_strategy = wait_exponential(multiplier=1, min=4, max=10)

    def decorator(func):
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_strategy,
            retry=retry_if_exception_type(retry_on),
            before_sleep=before_sleep_log(logger, logging.WARNING),
        )
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


def with_fallback(fallback_value: Any):
    """Decorator to provide fallback value on error."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Function {func.__name__} failed, using fallback: {e}")
                return fallback_value

        return wrapper

    return decorator


def with_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
):
    """Decorator to apply circuit breaker pattern."""
    breaker = CircuitBreaker(name, failure_threshold, recovery_timeout)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)

        return wrapper

    return decorator


def with_timeout(seconds: float):
    """Decorator to add timeout to function execution."""
    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError(f"Function execution exceeded {seconds} seconds")

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Set the timeout handler
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(seconds))

            try:
                result = func(*args, **kwargs)
            finally:
                # Disable the alarm
                signal.alarm(0)

            return result

        return wrapper

    return decorator


# Global error handler instance
_error_handler: ErrorHandler | None = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


# Custom exceptions with built-in recovery hints


class RecoverableError(Exception):
    """Base class for recoverable errors."""

    def __init__(
        self,
        message: str,
        recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.recovery_strategy = recovery_strategy
        self.severity = severity
        self.metadata = metadata or {}


class AuthenticationError(RecoverableError):
    """Authentication error with recovery hints."""

    def __init__(self, message: str, **metadata):
        super().__init__(
            message,
            recovery_strategy=RecoveryStrategy.FAIL_FAST,
            severity=ErrorSeverity.CRITICAL,
            metadata=metadata,
        )


class RateLimitError(RecoverableError):
    """Rate limit error with backoff hints."""

    def __init__(self, message: str, retry_after: int | None = None, **metadata):
        metadata["retry_after"] = retry_after
        super().__init__(
            message,
            recovery_strategy=RecoveryStrategy.RETRY,
            severity=ErrorSeverity.HIGH,
            metadata=metadata,
        )


class DataValidationError(RecoverableError):
    """Data validation error with fallback hints."""

    def __init__(self, message: str, field: str | None = None, **metadata):
        metadata["field"] = field
        super().__init__(
            message,
            recovery_strategy=RecoveryStrategy.FALLBACK,
            severity=ErrorSeverity.MEDIUM,
            metadata=metadata,
        )
