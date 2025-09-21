"""Unit tests for error handler module."""

import time
from unittest.mock import patch

import pytest

from ledzephyr.error_handler import (
    AuthenticationError,
    CircuitBreaker,
    DataValidationError,
    ErrorContext,
    ErrorHandler,
    ErrorSeverity,
    RateLimitError,
    RecoverableError,
    RecoveryStrategy,
    get_error_handler,
    with_circuit_breaker,
    with_fallback,
    with_retry,
    with_timeout,
)


@pytest.mark.unit
class TestErrorTypes:
    """Test custom error types."""

    def test_recoverable_error_creation(self):
        """Test RecoverableError creation."""
        error = RecoverableError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert isinstance(error, Exception)

    def test_authentication_error_creation(self):
        """Test AuthenticationError creation."""
        error = AuthenticationError("Invalid credentials")
        assert str(error) == "Invalid credentials"
        assert isinstance(error, RecoverableError)
        assert isinstance(error, Exception)

    def test_rate_limit_error_creation(self):
        """Test RateLimitError creation."""
        error = RateLimitError("API rate limit exceeded")
        assert str(error) == "API rate limit exceeded"
        assert isinstance(error, RecoverableError)

    def test_data_validation_error_creation(self):
        """Test DataValidationError creation."""
        error = DataValidationError("Invalid data format")
        assert str(error) == "Invalid data format"
        assert isinstance(error, RecoverableError)

    def test_error_inheritance(self):
        """Test error inheritance chain."""
        auth_error = AuthenticationError("Test")
        rate_error = RateLimitError("Test")
        validation_error = DataValidationError("Test")

        # All should be RecoverableError instances
        assert all(
            isinstance(e, RecoverableError) for e in [auth_error, rate_error, validation_error]
        )

        # All should be Exception instances
        assert all(isinstance(e, Exception) for e in [auth_error, rate_error, validation_error])


@pytest.mark.unit
class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_creation(self):
        """Test CircuitBreaker creation with default values."""
        breaker = CircuitBreaker("test_service")

        assert breaker.name == "test_service"
        assert breaker.failure_threshold == 5
        assert breaker.recovery_timeout == 60
        assert breaker.expected_exception == Exception
        assert breaker.failure_count == 0
        assert breaker.last_failure_time is None
        assert breaker.state == "closed"

    def test_circuit_breaker_creation_with_custom_values(self):
        """Test CircuitBreaker creation with custom values."""
        breaker = CircuitBreaker(
            "api_service",
            failure_threshold=3,
            recovery_timeout=30,
            expected_exception=ConnectionError,
        )

        assert breaker.name == "api_service"
        assert breaker.failure_threshold == 3
        assert breaker.recovery_timeout == 30
        assert breaker.expected_exception == ConnectionError

    def test_circuit_breaker_successful_call_closed_state(self):
        """Test successful function call in closed state."""
        breaker = CircuitBreaker("test")

        def success_func():
            return "success"

        result = breaker.call(success_func)

        assert result == "success"
        assert breaker.state == "closed"
        assert breaker.failure_count == 0

    def test_circuit_breaker_failed_call_below_threshold(self):
        """Test failed function call below failure threshold."""
        breaker = CircuitBreaker("test", failure_threshold=3)

        def failing_func():
            raise ConnectionError("Connection failed")

        with pytest.raises(ConnectionError):
            breaker.call(failing_func)

        assert breaker.state == "closed"  # Should remain closed
        assert breaker.failure_count == 1
        assert breaker.last_failure_time is not None

    def test_circuit_breaker_opens_at_failure_threshold(self):
        """Test circuit breaker opens when failure threshold is reached."""
        breaker = CircuitBreaker("test", failure_threshold=2)

        def failing_func():
            raise ConnectionError("Connection failed")

        # First failure
        with pytest.raises(ConnectionError):
            breaker.call(failing_func)
        assert breaker.state == "closed"
        assert breaker.failure_count == 1

        # Second failure - should open circuit
        with pytest.raises(ConnectionError):
            breaker.call(failing_func)
        assert breaker.state == "open"
        assert breaker.failure_count == 2

    def test_circuit_breaker_rejects_calls_when_open(self):
        """Test circuit breaker rejects calls when in open state."""
        breaker = CircuitBreaker("test", failure_threshold=1)

        def failing_func():
            raise ConnectionError("Connection failed")

        # Trigger opening
        with pytest.raises(ConnectionError):
            breaker.call(failing_func)
        assert breaker.state == "open"

        # Next call should be rejected immediately
        def any_func():
            return "should not be called"

        with pytest.raises(Exception, match="Circuit breaker test is open"):
            breaker.call(any_func)

    def test_circuit_breaker_half_open_transition(self):
        """Test circuit breaker transitions to half-open after timeout."""
        breaker = CircuitBreaker("test", failure_threshold=1, recovery_timeout=1)

        def failing_func():
            raise ConnectionError("Connection failed")

        # Open the circuit
        with pytest.raises(ConnectionError):
            breaker.call(failing_func)
        assert breaker.state == "open"

        # Wait for recovery timeout
        time.sleep(1.1)

        def success_func():
            return "success"

        # Should transition to half-open and then closed on success
        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.state == "closed"
        assert breaker.failure_count == 0

    def test_circuit_breaker_half_open_failure_reopens(self):
        """Test circuit breaker reopens if call fails in half-open state."""
        breaker = CircuitBreaker("test", failure_threshold=1, recovery_timeout=1)

        def failing_func():
            raise ConnectionError("Connection failed")

        # Open the circuit
        with pytest.raises(ConnectionError):
            breaker.call(failing_func)
        assert breaker.state == "open"

        # Wait for recovery timeout
        time.sleep(1.1)

        # Fail in half-open state - should reopen
        with pytest.raises(ConnectionError):
            breaker.call(failing_func)
        assert breaker.state == "open"

    def test_circuit_breaker_respects_expected_exception_type(self):
        """Test circuit breaker only responds to expected exception types."""
        breaker = CircuitBreaker("test", failure_threshold=1, expected_exception=ConnectionError)

        def func_with_different_exception():
            raise ValueError("Different error")

        # Should not trigger circuit breaker for different exception types
        with pytest.raises(ValueError):
            breaker.call(func_with_different_exception)

        assert breaker.state == "closed"
        assert breaker.failure_count == 0

    def test_circuit_breaker_call_with_args_and_kwargs(self):
        """Test circuit breaker passes through function arguments."""
        breaker = CircuitBreaker("test")

        def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = breaker.call(func_with_args, "arg1", "arg2", c="kwarg1")
        assert result == "arg1-arg2-kwarg1"


@pytest.mark.unit
class TestErrorHandler:
    """Test ErrorHandler functionality."""

    def test_error_handler_creation(self):
        """Test ErrorHandler creation with default values."""
        handler = ErrorHandler()

        assert isinstance(handler.error_history, list)
        assert len(handler.error_history) == 0
        assert isinstance(handler.circuit_breakers, dict)
        assert isinstance(handler.fallback_values, dict)
        assert isinstance(handler.recovery_strategies, dict)

        # Check default recovery strategies
        assert handler.recovery_strategies[ConnectionError] == RecoveryStrategy.RETRY
        assert handler.recovery_strategies[TimeoutError] == RecoveryStrategy.CIRCUIT_BREAK
        assert handler.recovery_strategies[ValueError] == RecoveryStrategy.FALLBACK
        assert handler.recovery_strategies[KeyError] == RecoveryStrategy.DEGRADE
        assert handler.recovery_strategies[PermissionError] == RecoveryStrategy.FAIL_FAST

    def test_register_circuit_breaker(self):
        """Test registering a circuit breaker."""
        handler = ErrorHandler()

        breaker = handler.register_circuit_breaker(
            "test_service", failure_threshold=3, recovery_timeout=30
        )

        assert "test_service" in handler.circuit_breakers
        assert handler.circuit_breakers["test_service"] is breaker
        assert breaker.name == "test_service"
        assert breaker.failure_threshold == 3
        assert breaker.recovery_timeout == 30

    def test_register_fallback(self):
        """Test registering fallback values."""
        handler = ErrorHandler()

        handler.register_fallback("api_call", "fallback_value")
        handler.register_fallback("database_query", None)

        assert handler.fallback_values["api_call"] == "fallback_value"
        assert handler.fallback_values["database_query"] is None

    def test_determine_severity_for_critical_errors(self):
        """Test severity determination for critical errors."""
        handler = ErrorHandler()

        auth_error = AuthenticationError("Invalid token")
        perm_error = PermissionError("Access denied")

        assert handler._determine_severity(auth_error) == ErrorSeverity.CRITICAL
        assert handler._determine_severity(perm_error) == ErrorSeverity.CRITICAL

    def test_determine_severity_for_high_errors(self):
        """Test severity determination for high severity errors."""
        handler = ErrorHandler()

        conn_error = ConnectionError("Connection lost")
        timeout_error = TimeoutError("Request timeout")

        assert handler._determine_severity(conn_error) == ErrorSeverity.HIGH
        assert handler._determine_severity(timeout_error) == ErrorSeverity.HIGH

    def test_determine_severity_for_medium_errors(self):
        """Test severity determination for medium severity errors."""
        handler = ErrorHandler()

        value_error = ValueError("Invalid value")
        key_error = KeyError("Missing key")

        assert handler._determine_severity(value_error) == ErrorSeverity.MEDIUM
        assert handler._determine_severity(key_error) == ErrorSeverity.MEDIUM

    def test_determine_severity_for_low_errors(self):
        """Test severity determination for low severity errors."""
        handler = ErrorHandler()

        runtime_error = RuntimeError("Runtime issue")
        assert handler._determine_severity(runtime_error) == ErrorSeverity.LOW

    def test_handle_error_with_retry_strategy(self):
        """Test error handling with retry strategy."""
        handler = ErrorHandler()

        error = ConnectionError("Connection failed")
        result = handler.handle_error(error, operation="api_call")

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.RETRY
        assert "Retry 1/3" in result.message
        assert len(handler.error_history) == 1

        context = handler.error_history[0]
        assert context.error_type == ConnectionError
        assert context.error_message == "Connection failed"
        assert context.operation == "api_call"
        assert context.severity == ErrorSeverity.HIGH

    def test_handle_error_with_fallback_strategy(self):
        """Test error handling with fallback strategy."""
        handler = ErrorHandler()
        handler.register_fallback("test_operation", "fallback_result")

        error = ValueError("Invalid input")
        result = handler.handle_error(error, operation="test_operation")

        assert result.success
        assert result.strategy_used == RecoveryStrategy.FALLBACK
        assert result.value == "fallback_result"
        assert result.degraded
        assert result.message == "Using fallback value"

    def test_handle_error_with_fallback_strategy_no_fallback_available(self):
        """Test error handling with fallback strategy when no fallback is registered."""
        handler = ErrorHandler()

        error = ValueError("Invalid input")
        result = handler.handle_error(error, operation="missing_operation")

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.FALLBACK
        assert result.error is not None
        assert "No fallback available" in str(result.error)

    def test_handle_error_with_degrade_strategy(self):
        """Test error handling with degrade strategy."""
        handler = ErrorHandler()

        error = KeyError("Missing key")
        result = handler.handle_error(error, operation="data_access")

        assert result.success
        assert result.strategy_used == RecoveryStrategy.DEGRADE
        assert result.value is None
        assert result.degraded
        assert result.message == "Service degraded but operational"

    def test_handle_error_with_fail_fast_strategy(self):
        """Test error handling with fail fast strategy."""
        handler = ErrorHandler()

        error = PermissionError("Access denied")
        result = handler.handle_error(error, operation="secure_operation")

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.FAIL_FAST
        assert result.error is not None
        assert "Access denied" in str(result.error)

    def test_handle_error_with_circuit_break_strategy_closed_circuit(self):
        """Test error handling with circuit break strategy when circuit is closed."""
        handler = ErrorHandler()

        error = TimeoutError("Request timeout")
        result = handler.handle_error(error, operation="external_api")

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.CIRCUIT_BREAK
        assert "Circuit breaker allowing retry" in result.message

        # Verify circuit breaker was created
        assert "external_api" in handler.circuit_breakers

    def test_handle_error_with_circuit_break_strategy_open_circuit(self):
        """Test error handling with circuit break strategy when circuit is open."""
        handler = ErrorHandler()

        # Pre-register a circuit breaker and open it
        breaker = handler.register_circuit_breaker("external_api", failure_threshold=1)
        breaker.state = "open"  # Manually set to open for testing

        error = TimeoutError("Request timeout")
        result = handler.handle_error(error, operation="external_api")

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.CIRCUIT_BREAK
        assert "Circuit breaker external_api is open" in str(result.error)

    def test_error_context_manager_success(self):
        """Test error context manager with successful operation."""
        handler = ErrorHandler()

        with handler.error_context("test_operation"):
            result = "success"

        # No errors should be recorded for successful operations
        assert len(handler.error_history) == 0

    def test_error_context_manager_with_fallback(self):
        """Test error context manager with fallback value."""
        handler = ErrorHandler()

        # This should register the fallback and handle the error
        with handler.error_context("test_operation", fallback_value="fallback"):
            raise ValueError("Test error")

        # Error should be handled and fallback used
        assert len(handler.error_history) == 1
        assert handler.fallback_values["test_operation"] == "fallback"

    def test_error_context_manager_reraise_false(self):
        """Test error context manager with reraise=False."""
        handler = ErrorHandler()

        result = None
        with handler.error_context("test_operation", fallback_value="fallback", reraise=False):
            raise ValueError("Test error")

        # Should not reraise, error should be in history
        assert len(handler.error_history) == 1

    def test_get_error_stats_empty(self):
        """Test getting error statistics with no errors."""
        handler = ErrorHandler()

        stats = handler.get_error_stats()

        assert stats == {"total_errors": 0}

    def test_get_error_stats_with_errors(self):
        """Test getting error statistics with multiple errors."""
        handler = ErrorHandler()

        # Create some errors to populate statistics
        handler.handle_error(ConnectionError("Connection failed"), operation="api_call")
        handler.handle_error(ValueError("Invalid value"), operation="validation")
        handler.handle_error(ConnectionError("Another connection error"), operation="api_call2")

        stats = handler.get_error_stats()

        assert stats["total_errors"] == 3
        assert stats["errors_by_severity"]["high"] == 2  # Two ConnectionErrors
        assert stats["errors_by_severity"]["medium"] == 1  # One ValueError
        assert stats["errors_by_type"]["ConnectionError"] == 2
        assert stats["errors_by_type"]["ValueError"] == 1
        assert len(stats["recent_errors"]) == 3

        # Check recent errors format
        recent_error = stats["recent_errors"][0]
        assert "timestamp" in recent_error
        assert "operation" in recent_error
        assert "error" in recent_error
        assert "severity" in recent_error

    def test_get_error_stats_with_circuit_breakers(self):
        """Test error statistics include circuit breaker states."""
        handler = ErrorHandler()

        # Register some circuit breakers
        breaker1 = handler.register_circuit_breaker("service1", failure_threshold=3)
        breaker2 = handler.register_circuit_breaker("service2", failure_threshold=5)

        # Modify one breaker state
        breaker1.failure_count = 2

        # Add an error to trigger full stats generation
        handler.handle_error(ValueError("Test error"), operation="test")

        stats = handler.get_error_stats()

        assert "circuit_breakers" in stats
        assert stats["circuit_breakers"]["service1"]["state"] == "closed"
        assert stats["circuit_breakers"]["service1"]["failure_count"] == 2
        assert stats["circuit_breakers"]["service2"]["state"] == "closed"
        assert stats["circuit_breakers"]["service2"]["failure_count"] == 0

    def test_retry_recovery_max_retries_not_exceeded(self):
        """Test retry recovery when max retries not exceeded."""
        handler = ErrorHandler()

        context = ErrorContext(
            error_type=ConnectionError,
            error_message="Connection failed",
            severity=ErrorSeverity.HIGH,
            retry_count=1,
            max_retries=3,
        )

        result = handler._retry_recovery(context)

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.RETRY
        assert "Retry 2/3" in result.message

    def test_retry_recovery_max_retries_exceeded(self):
        """Test retry recovery when max retries exceeded."""
        handler = ErrorHandler()

        context = ErrorContext(
            error_type=ConnectionError,
            error_message="Connection failed",
            severity=ErrorSeverity.HIGH,
            retry_count=3,
            max_retries=3,
        )

        result = handler._retry_recovery(context)

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.RETRY
        assert result.error is not None
        assert "Max retries exceeded" in str(result.error)


@pytest.mark.unit
class TestDecorators:
    """Test decorator functions."""

    def test_with_fallback_decorator_success(self):
        """Test with_fallback decorator on successful function."""

        @with_fallback("fallback_value")
        def success_func():
            return "success"

        result = success_func()
        assert result == "success"

    def test_with_fallback_decorator_failure(self):
        """Test with_fallback decorator on failing function."""

        @with_fallback("fallback_value")
        def failing_func():
            raise ValueError("Function failed")

        result = failing_func()
        assert result == "fallback_value"

    def test_with_circuit_breaker_decorator_success(self):
        """Test with_circuit_breaker decorator on successful function."""

        @with_circuit_breaker("test_service", failure_threshold=2)
        def success_func():
            return "success"

        result = success_func()
        assert result == "success"

    def test_with_circuit_breaker_decorator_failure_below_threshold(self):
        """Test with_circuit_breaker decorator failure below threshold."""

        @with_circuit_breaker("test_service", failure_threshold=2)
        def failing_func():
            raise ConnectionError("Connection failed")

        # First failure should be raised
        with pytest.raises(ConnectionError):
            failing_func()

    def test_with_circuit_breaker_decorator_opens_at_threshold(self):
        """Test with_circuit_breaker decorator opens at failure threshold."""

        @with_circuit_breaker("test_service", failure_threshold=1)
        def failing_func():
            raise ConnectionError("Connection failed")

        # First failure opens the circuit
        with pytest.raises(ConnectionError):
            failing_func()

        # Second call should be rejected by open circuit
        with pytest.raises(Exception, match="Circuit breaker test_service is open"):
            failing_func()

    def test_with_retry_decorator_success(self):
        """Test with_retry decorator on successful function."""

        @with_retry(max_attempts=3)
        def success_func():
            return "success"

        result = success_func()
        assert result == "success"

    def test_with_retry_decorator_eventual_success(self):
        """Test with_retry decorator eventually succeeds after failures."""
        call_count = 0

        @with_retry(max_attempts=3, retry_on=(ValueError,))
        def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = eventually_succeeds()
        assert result == "success"
        assert call_count == 3

    def test_with_retry_decorator_max_attempts_exceeded(self):
        """Test with_retry decorator when max attempts exceeded."""
        from tenacity import RetryError

        @with_retry(max_attempts=2, retry_on=(ValueError,))
        def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(RetryError):
            always_fails()

    @patch("signal.signal")
    @patch("signal.alarm")
    def test_with_timeout_decorator_success(self, mock_alarm, mock_signal):
        """Test with_timeout decorator on successful function."""

        @with_timeout(5.0)
        def success_func():
            return "success"

        result = success_func()
        assert result == "success"

        # Verify timeout setup and cleanup
        mock_signal.assert_called()
        mock_alarm.assert_any_call(5)  # Set timeout
        mock_alarm.assert_any_call(0)  # Clear timeout

    @patch("signal.signal")
    @patch("signal.alarm")
    def test_with_timeout_decorator_timeout_not_triggered(self, mock_alarm, mock_signal):
        """Test with_timeout decorator when timeout is not triggered."""

        @with_timeout(1.0)
        def fast_func():
            return "fast"

        result = fast_func()
        assert result == "fast"


@pytest.mark.unit
class TestGlobalErrorHandler:
    """Test global error handler functionality."""

    def test_get_error_handler_singleton(self):
        """Test global error handler is singleton."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()

        assert handler1 is handler2
        assert isinstance(handler1, ErrorHandler)

    def test_global_error_handler_persistence(self):
        """Test global error handler persists state."""
        handler1 = get_error_handler()
        handler1.register_fallback("test", "value")

        handler2 = get_error_handler()
        assert handler2.fallback_values["test"] == "value"


@pytest.mark.unit
class TestCustomExceptionProperties:
    """Test custom exception properties and metadata."""

    def test_recoverable_error_with_metadata(self):
        """Test RecoverableError with custom metadata."""
        metadata = {"user_id": "123", "request_id": "abc"}
        error = RecoverableError(
            "Test error",
            recovery_strategy=RecoveryStrategy.RETRY,
            severity=ErrorSeverity.HIGH,
            metadata=metadata,
        )

        assert str(error) == "Test error"
        assert error.recovery_strategy == RecoveryStrategy.RETRY
        assert error.severity == ErrorSeverity.HIGH
        assert error.metadata == metadata

    def test_authentication_error_properties(self):
        """Test AuthenticationError has correct properties."""
        error = AuthenticationError("Invalid token", user_id="123")

        assert str(error) == "Invalid token"
        assert error.recovery_strategy == RecoveryStrategy.FAIL_FAST
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.metadata["user_id"] == "123"

    def test_rate_limit_error_properties(self):
        """Test RateLimitError has correct properties."""
        error = RateLimitError("Rate limit exceeded", retry_after=60, api_key="abc123")

        assert str(error) == "Rate limit exceeded"
        assert error.recovery_strategy == RecoveryStrategy.RETRY
        assert error.severity == ErrorSeverity.HIGH
        assert error.metadata["retry_after"] == 60
        assert error.metadata["api_key"] == "abc123"

    def test_data_validation_error_properties(self):
        """Test DataValidationError has correct properties."""
        error = DataValidationError("Invalid format", field="email", value="invalid@")

        assert str(error) == "Invalid format"
        assert error.recovery_strategy == RecoveryStrategy.FALLBACK
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.metadata["field"] == "email"
        assert error.metadata["value"] == "invalid@"
