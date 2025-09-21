"""Unit tests for error handler module."""

import pytest

from ledzephyr.error_handler import (
    AuthenticationError,
    DataValidationError,
    RateLimitError,
    RecoverableError,
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
