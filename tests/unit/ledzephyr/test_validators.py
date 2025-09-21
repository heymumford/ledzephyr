"""Unit tests for validators module following TDD methodology.

This module provides comprehensive test coverage for all validation functionality
including data validation, sanitization, and error handling.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from ledzephyr.validators import (
    APITokenValidator,
    DataSanitizer,
    EmailValidator,
    InputValidator,
    MetricsRequestValidator,
    ProjectKeyValidator,
    TestCaseValidator,
    TimeWindowValidator,
    URLValidator,
    ValidationLevel,
    ValidationResult,
    get_validator,
)


@pytest.mark.unit
class TestValidationLevel:
    """Test ValidationLevel enum."""

    def test_validation_level_enum_has_strict_value(self):
        """Test ValidationLevel enum has STRICT value."""
        # Act & Assert
        assert ValidationLevel.STRICT.value == "strict"

    def test_validation_level_enum_has_moderate_value(self):
        """Test ValidationLevel enum has MODERATE value."""
        # Act & Assert
        assert ValidationLevel.MODERATE.value == "moderate"

    def test_validation_level_enum_has_lenient_value(self):
        """Test ValidationLevel enum has LENIENT value."""
        # Act & Assert
        assert ValidationLevel.LENIENT.value == "lenient"


@pytest.mark.unit
class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_validation_result_creation_default_values_creates_instance(self):
        """Test ValidationResult creation with default values creates instance."""
        # Act
        result = ValidationResult[str](valid=True)

        # Assert
        assert result.valid is True
        assert result.value is None
        assert result.errors == []
        assert result.warnings == []
        assert result.sanitized is False

    def test_validation_result_creation_with_value_sets_value(self):
        """Test ValidationResult creation with value sets value correctly."""
        # Act
        result = ValidationResult[str](valid=True, value="test_value")

        # Assert
        assert result.valid is True
        assert result.value == "test_value"

    def test_validation_result_creation_with_errors_sets_errors(self):
        """Test ValidationResult creation with errors sets errors correctly."""
        # Arrange
        errors = ["Error 1", "Error 2"]

        # Act
        result = ValidationResult[str](valid=False, errors=errors)

        # Assert
        assert result.valid is False
        assert result.errors == errors

    def test_validation_result_creation_with_warnings_sets_warnings(self):
        """Test ValidationResult creation with warnings sets warnings correctly."""
        # Arrange
        warnings = ["Warning 1", "Warning 2"]

        # Act
        result = ValidationResult[str](valid=True, warnings=warnings)

        # Assert
        assert result.valid is True
        assert result.warnings == warnings

    def test_validation_result_creation_with_sanitized_flag_sets_flag(self):
        """Test ValidationResult creation with sanitized flag sets flag correctly."""
        # Act
        result = ValidationResult[str](valid=True, sanitized=True)

        # Assert
        assert result.valid is True
        assert result.sanitized is True


# This is our first failing test - we need these fixtures to exist
@pytest.fixture
def valid_project_keys():
    """Provide valid project key test data."""
    return ["AB", "TEST", "PROJ123", "A1B2C3D4E5"]


@pytest.fixture
def invalid_project_keys():
    """Provide invalid project key test data."""
    return ["", "a", "test", "AB-123", "TOOLONGKEY123", "1AB", "AB_CD"]


@pytest.fixture
def valid_time_windows():
    """Provide valid time window test data."""
    return ["1h", "24h", "7d", "30d", "4w", "12m", "1H", "1D", "1W", "1M"]


@pytest.fixture
def invalid_time_windows():
    """Provide invalid time window test data."""
    return ["", "1", "1x", "745h", "366d", "53w", "13m", "1hr", "1day"]


@pytest.fixture
def zero_time_windows():
    """Provide zero value time windows that should be invalid."""
    return ["0h", "0d", "0w", "0m"]


@pytest.fixture
def valid_emails():
    """Provide valid email test data."""
    return [
        "test@example.com",
        "user.name@domain.co.uk",
        "firstname+lastname@company.org",
        "test123@sub.domain.com",
        "a@b.co",
    ]


@pytest.fixture
def invalid_emails():
    """Provide invalid email test data."""
    return [
        "",
        "not_an_email",
        "@domain.com",
        "user@",
        "user@domain",
        "user space@domain.com",
        "a" * 250 + "@domain.com",  # Too long
    ]


@pytest.fixture
def double_dot_emails():
    """Provide emails with double dots that should be invalid."""
    return ["user@domain..com", "test@..example.com", "admin@domain.com.."]


@pytest.fixture
def typo_emails():
    """Provide emails with common typos."""
    return {
        "test@gmial.com": "gmail.com",
        "user@gmai.com": "gmail.com",
        "person@yahooo.com": "yahoo.com",
        "admin@outlok.com": "outlook.com",
    }


@pytest.mark.unit
class TestProjectKeyValidator:
    """Test ProjectKeyValidator class."""

    def test_project_key_validator_valid_key_succeeds(self, valid_project_keys):
        """Test ProjectKeyValidator with valid key succeeds."""
        for key in valid_project_keys:
            # Act
            validator = ProjectKeyValidator(key=key)

            # Assert
            assert validator.key == key

    def test_project_key_validator_invalid_key_raises_validation_error(self, invalid_project_keys):
        """Test ProjectKeyValidator with invalid key raises ValidationError."""
        for key in invalid_project_keys:
            # Act & Assert
            with pytest.raises(ValidationError):
                ProjectKeyValidator(key=key)

    def test_project_key_validator_lowercase_key_raises_validation_error(self):
        """Test ProjectKeyValidator with lowercase key raises ValidationError."""
        # Act & Assert
        with pytest.raises(ValidationError, match="String should match pattern"):
            ProjectKeyValidator(key="test")

    def test_project_key_validator_test_key_logs_warning(self):
        """Test ProjectKeyValidator with test key logs warning."""
        # This test will initially fail because we need to verify the warning is logged
        with patch("ledzephyr.validators.logger.warning") as mock_warning:
            # Act
            ProjectKeyValidator(key="TEST")

            # Assert
            mock_warning.assert_called_once_with("Using test project key: TEST")

    def test_project_key_validator_demo_key_logs_warning(self):
        """Test ProjectKeyValidator with demo key logs warning."""
        with patch("ledzephyr.validators.logger.warning") as mock_warning:
            # Act
            ProjectKeyValidator(key="DEMO")

            # Assert
            mock_warning.assert_called_once_with("Using test project key: DEMO")

    def test_project_key_validator_temp_key_logs_warning(self):
        """Test ProjectKeyValidator with temp key logs warning."""
        with patch("ledzephyr.validators.logger.warning") as mock_warning:
            # Act
            ProjectKeyValidator(key="TEMP")

            # Assert
            mock_warning.assert_called_once_with("Using test project key: TEMP")


@pytest.mark.unit
class TestTimeWindowValidator:
    """Test TimeWindowValidator class."""

    def test_time_window_validator_valid_windows_succeed(self, valid_time_windows):
        """Test TimeWindowValidator with valid windows succeeds."""
        for window in valid_time_windows:
            # Act
            validator = TimeWindowValidator(window=window)

            # Assert
            assert validator.window == window

    def test_time_window_validator_invalid_windows_raise_validation_error(
        self, invalid_time_windows
    ):
        """Test TimeWindowValidator with invalid windows raises ValidationError."""
        for window in invalid_time_windows:
            # Act & Assert
            with pytest.raises(ValidationError):
                TimeWindowValidator(window=window)

    def test_time_window_validator_hour_limit_exceeded_raises_validation_error(self):
        """Test TimeWindowValidator with hour limit exceeded raises ValidationError."""
        # Act & Assert
        with pytest.raises(ValidationError, match="Hour window cannot exceed 744 hours"):
            TimeWindowValidator(window="745h")

    def test_time_window_validator_day_limit_exceeded_raises_validation_error(self):
        """Test TimeWindowValidator with day limit exceeded raises ValidationError."""
        # Act & Assert
        with pytest.raises(ValidationError, match="Day window cannot exceed 365 days"):
            TimeWindowValidator(window="366d")

    def test_time_window_validator_week_limit_exceeded_raises_validation_error(self):
        """Test TimeWindowValidator with week limit exceeded raises ValidationError."""
        # Act & Assert
        with pytest.raises(ValidationError, match="Week window cannot exceed 52 weeks"):
            TimeWindowValidator(window="53w")

    def test_time_window_validator_month_limit_exceeded_raises_validation_error(self):
        """Test TimeWindowValidator with month limit exceeded raises ValidationError."""
        # Act & Assert
        with pytest.raises(ValidationError, match="Month window cannot exceed 12 months"):
            TimeWindowValidator(window="13m")

    def test_time_window_validator_to_timedelta_hours_returns_correct_delta(self):
        """Test TimeWindowValidator to_timedelta with hours returns correct timedelta."""
        # Arrange
        validator = TimeWindowValidator(window="24h")

        # Act
        result = validator.to_timedelta()

        # Assert
        assert result == timedelta(hours=24)

    def test_time_window_validator_to_timedelta_days_returns_correct_delta(self):
        """Test TimeWindowValidator to_timedelta with days returns correct timedelta."""
        # Arrange
        validator = TimeWindowValidator(window="7d")

        # Act
        result = validator.to_timedelta()

        # Assert
        assert result == timedelta(days=7)

    def test_time_window_validator_to_timedelta_weeks_returns_correct_delta(self):
        """Test TimeWindowValidator to_timedelta with weeks returns correct timedelta."""
        # Arrange
        validator = TimeWindowValidator(window="4w")

        # Act
        result = validator.to_timedelta()

        # Assert
        assert result == timedelta(weeks=4)

    def test_time_window_validator_to_timedelta_months_returns_correct_delta(self):
        """Test TimeWindowValidator to_timedelta with months returns correct timedelta."""
        # Arrange
        validator = TimeWindowValidator(window="3m")

        # Act
        result = validator.to_timedelta()

        # Assert
        assert result == timedelta(days=90)  # 3 * 30 days

    def test_time_window_validator_case_insensitive_succeeds(self):
        """Test TimeWindowValidator accepts uppercase and lowercase units."""
        # Arrange & Act
        validator_lower = TimeWindowValidator(window="1h")
        validator_upper = TimeWindowValidator(window="1H")

        # Assert
        assert validator_lower.window == "1h"
        assert validator_upper.window == "1H"

    def test_time_window_validator_zero_values_raise_validation_error(self, zero_time_windows):
        """Test TimeWindowValidator with zero values raises ValidationError."""
        for window in zero_time_windows:
            # Act & Assert
            with pytest.raises(ValidationError):
                TimeWindowValidator(window=window)


@pytest.mark.unit
class TestEmailValidator:
    """Test EmailValidator class."""

    def test_email_validator_valid_emails_succeed(self, valid_emails):
        """Test EmailValidator with valid emails succeeds."""
        for email in valid_emails:
            # Act
            validator = EmailValidator(email=email)

            # Assert
            assert validator.email == email.lower()  # Should be normalized to lowercase

    def test_email_validator_invalid_emails_raise_validation_error(self, invalid_emails):
        """Test EmailValidator with invalid emails raises ValidationError."""
        for email in invalid_emails:
            # Act & Assert
            with pytest.raises(ValidationError):
                EmailValidator(email=email)

    def test_email_validator_normalizes_to_lowercase(self):
        """Test EmailValidator normalizes emails to lowercase."""
        # Arrange
        email = "TEST@EXAMPLE.COM"

        # Act
        validator = EmailValidator(email=email)

        # Assert
        assert validator.email == "test@example.com"

    def test_email_validator_typo_domains_log_warnings(self, typo_emails):
        """Test EmailValidator logs warnings for typo domains."""
        for typo_email, correct_domain in typo_emails.items():
            with patch("ledzephyr.validators.logger.warning") as mock_warning:
                # Act
                EmailValidator(email=typo_email)

                # Assert
                mock_warning.assert_called_once()
                args = mock_warning.call_args[0]
                assert "Possible typo in email domain" in args[0]
                assert typo_email.split("@")[1] in args[0]

    def test_email_validator_accepts_long_valid_email(self):
        """Test EmailValidator accepts valid emails up to length limit."""
        # Arrange - Create a valid email just under the 254 character limit
        local_part = "a" * 60
        domain_part = "b" * 60 + ".com"
        valid_long_email = f"{local_part}@{domain_part}"

        # Act
        validator = EmailValidator(email=valid_long_email)

        # Assert
        assert validator.email == valid_long_email.lower()

    def test_email_validator_double_dot_domains_raise_validation_error(self, double_dot_emails):
        """Test EmailValidator with double dot domains raises ValidationError."""
        for email in double_dot_emails:
            # Act & Assert
            with pytest.raises(ValidationError):
                EmailValidator(email=email)


@pytest.fixture
def valid_urls():
    """Provide valid URL test data."""
    return [
        "https://example.com",
        "http://localhost:8080",
        "https://sub.domain.com/path",
        "https://192.168.1.1:8080",
        "https://test.atlassian.net",
    ]


@pytest.fixture
def invalid_urls():
    """Provide invalid URL test data."""
    return [
        "",
        "not_a_url",
        "ftp://example.com",
        "https://",
        "http://",
        "https://space domain.com",
    ]


@pytest.fixture
def valid_api_tokens():
    """Provide valid API token test data."""
    return [
        "a" * 20,  # Minimum length
        "valid_token_123456789",
        "Bearer " + "a" * 20,  # With Bearer prefix, long enough after removal
        "Token " + "b" * 20,  # With Token prefix, long enough after removal
        "Basic " + "c" * 20,  # With Basic prefix, long enough after removal
    ]


@pytest.fixture
def invalid_api_tokens():
    """Provide invalid API token test data."""
    return [
        "",
        "short",  # Too short
        "a" * 19,  # Just under minimum
        "your-token-here",  # Placeholder
        "xxx",  # Placeholder
        "token with spaces",  # Contains spaces
        "token\nwith\nnewlines",  # Contains newlines
    ]


@pytest.mark.unit
class TestURLValidator:
    """Test URLValidator class."""

    def test_url_validator_valid_urls_succeed(self, valid_urls):
        """Test URLValidator with valid URLs succeeds."""
        for url in valid_urls:
            # Act
            validator = URLValidator(url=url)

            # Assert
            assert validator.url == url.rstrip("/")  # Trailing slashes removed

    def test_url_validator_invalid_urls_raise_validation_error(self, invalid_urls):
        """Test URLValidator with invalid URLs raises ValidationError."""
        for url in invalid_urls:
            # Act & Assert
            with pytest.raises(ValidationError):
                URLValidator(url=url)

    def test_url_validator_removes_trailing_slash(self):
        """Test URLValidator removes trailing slashes."""
        # Arrange
        url_with_slash = "https://example.com/"

        # Act
        validator = URLValidator(url=url_with_slash)

        # Assert
        assert validator.url == "https://example.com"

    def test_url_validator_atlassian_requires_https(self):
        """Test URLValidator requires HTTPS for Atlassian URLs."""
        # Act & Assert
        with pytest.raises(ValidationError, match="Atlassian URLs must use HTTPS"):
            URLValidator(url="http://test.atlassian.net")

    def test_url_validator_atlassian_https_succeeds(self):
        """Test URLValidator accepts HTTPS Atlassian URLs."""
        # Act
        validator = URLValidator(url="https://test.atlassian.net")

        # Assert
        assert validator.url == "https://test.atlassian.net"


@pytest.mark.unit
class TestAPITokenValidator:
    """Test APITokenValidator class."""

    def test_api_token_validator_valid_tokens_succeed(self, valid_api_tokens):
        """Test APITokenValidator with valid tokens succeeds."""
        for token in valid_api_tokens:
            # Act
            validator = APITokenValidator(token=token)

            # Assert - Should strip prefixes and whitespace
            expected = (
                token.replace("Bearer ", "").replace("Token ", "").replace("Basic ", "").strip()
            )
            assert validator.token == expected

    def test_api_token_validator_invalid_tokens_raise_validation_error(self, invalid_api_tokens):
        """Test APITokenValidator with invalid tokens raises ValidationError."""
        for token in invalid_api_tokens:
            # Act & Assert
            with pytest.raises(ValidationError):
                APITokenValidator(token=token)

    def test_api_token_validator_strips_bearer_prefix(self):
        """Test APITokenValidator strips Bearer prefix."""
        # Arrange
        token_with_prefix = "Bearer " + "a" * 25  # Long enough token

        # Act
        validator = APITokenValidator(token=token_with_prefix)

        # Assert
        assert validator.token == "a" * 25

    def test_api_token_validator_placeholder_tokens_raise_validation_error(self):
        """Test APITokenValidator rejects exact placeholder tokens."""
        # Test tokens that will pass length validation but trigger placeholder validation
        # We need tokens that when processed (prefix removed, stripped) become exactly the placeholders

        # Test the case where after prefix removal we get exactly "your-token-here"
        with pytest.raises(ValidationError, match="Invalid placeholder token"):
            APITokenValidator(token="Bearer your-token-here")

        # For xxx case, we can't easily test the placeholder validation because
        # any padding would trigger other validations. Let's test the invalid
        # characters validation instead.
        with pytest.raises(ValidationError, match="Token contains invalid characters"):
            APITokenValidator(token="token with spaces and enough characters")


@pytest.mark.unit
class TestDataSanitizer:
    """Test DataSanitizer class."""

    def test_sanitize_string_basic_functionality(self):
        """Test DataSanitizer sanitize_string basic functionality."""
        # Arrange
        input_string = "  Hello   World  "

        # Act
        result = DataSanitizer.sanitize_string(input_string)

        # Assert
        assert result == "Hello World"

    def test_sanitize_string_removes_html_by_default(self):
        """Test DataSanitizer sanitize_string removes HTML by default."""
        # Arrange
        input_string = "<script>alert('xss')</script>Hello <b>World</b>"

        # Act
        result = DataSanitizer.sanitize_string(input_string)

        # Assert
        assert "<script>" not in result
        assert "<b>" not in result
        assert "Hello" in result
        assert "World" in result

    def test_sanitize_string_truncates_to_max_length(self):
        """Test DataSanitizer sanitize_string truncates to max length."""
        # Arrange
        long_string = "a" * 2000

        # Act
        result = DataSanitizer.sanitize_string(long_string, max_length=100)

        # Assert
        assert len(result) == 100

    def test_sanitize_string_removes_null_bytes(self):
        """Test DataSanitizer sanitize_string removes null bytes."""
        # Arrange
        input_string = "Hello\x00World"

        # Act
        result = DataSanitizer.sanitize_string(input_string)

        # Assert
        assert "\x00" not in result
        assert result == "HelloWorld"

    def test_sanitize_filename_basic_functionality(self):
        """Test DataSanitizer sanitize_filename basic functionality."""
        # Arrange
        dangerous_filename = "../../../etc/passwd"

        # Act
        result = DataSanitizer.sanitize_filename(dangerous_filename)

        # Assert
        assert ".." not in result
        assert "/" not in result
        assert "\\" not in result

    def test_sanitize_filename_limits_length(self):
        """Test DataSanitizer sanitize_filename limits length."""
        # Arrange
        long_filename = "a" * 300 + ".txt"

        # Act
        result = DataSanitizer.sanitize_filename(long_filename)

        # Assert
        assert len(result) <= 204  # 200 + ".txt"
        assert result.endswith(".txt")

    def test_sanitize_sql_identifier_removes_special_chars(self):
        """Test DataSanitizer sanitize_sql_identifier removes special characters."""
        # Arrange
        dangerous_identifier = "user'; DROP TABLE users; --"

        # Act
        result = DataSanitizer.sanitize_sql_identifier(dangerous_identifier)

        # Assert
        assert "'" not in result
        assert ";" not in result
        assert "-" not in result
        assert " " not in result
        assert len(result) <= 64

    def test_sanitize_json_data_handles_nested_structures(self):
        """Test DataSanitizer sanitize_json_data handles nested structures."""
        # Arrange
        data = {
            "<script>key</script>": "<b>value</b>",
            "nested": {"list": ["<i>item1</i>", "<u>item2</u>"]},
        }

        # Act
        result = DataSanitizer.sanitize_json_data(data)

        # Assert
        assert "<script>" not in str(result)
        assert "<b>" not in str(result)
        assert "<i>" not in str(result)
        assert "<u>" not in str(result)
        assert "value" in str(result)
        assert "item1" in str(result)

    def test_sanitize_string_allows_safe_html_when_enabled(self):
        """Test DataSanitizer sanitize_string allows safe HTML when enabled."""
        # Arrange
        input_string = "Hello <b>World</b> <script>alert('xss')</script>"

        # Act
        result = DataSanitizer.sanitize_string(input_string, allow_html=True)

        # Assert
        assert "<b>World</b>" in result  # Safe tag allowed
        assert "<script>" not in result  # Unsafe tag removed


@pytest.mark.unit
class TestTestCaseValidator:
    """Test TestCaseValidator class."""

    def test_test_case_validator_valid_data_succeeds(self):
        """Test TestCaseValidator with valid data succeeds."""
        # Arrange
        valid_data = {
            "key": "TEST-123",
            "summary": "Test case summary",
            "status": "Open",
            "component": "Frontend",
            "labels": ["ui", "critical"],
        }

        # Act
        validator = TestCaseValidator(**valid_data)

        # Assert
        assert validator.key == "TEST-123"
        assert validator.summary == "Test case summary"
        assert validator.status == "Open"
        assert validator.component == "Frontend"
        assert "ui" in validator.labels
        assert "critical" in validator.labels

    def test_test_case_validator_sanitizes_summary_html(self):
        """Test TestCaseValidator sanitizes HTML in summary."""
        # Arrange
        data = {
            "key": "TEST-123",
            "summary": "<script>alert('xss')</script>Clean <b>summary</b> text",
        }

        # Act
        validator = TestCaseValidator(**data)

        # Assert
        assert "<script>" not in validator.summary
        assert "<b>" not in validator.summary
        assert "Clean" in validator.summary
        assert "summary" in validator.summary

    def test_test_case_validator_normalizes_labels(self):
        """Test TestCaseValidator normalizes and deduplicates labels."""
        # Arrange
        data = {
            "key": "TEST-123",
            "summary": "Test summary",
            "labels": ["UI", "Critical", "ui", "test@label", ""],
        }

        # Act
        validator = TestCaseValidator(**data)

        # Assert
        assert "ui" in validator.labels
        assert "critical" in validator.labels
        assert "testlabel" in validator.labels  # Special chars removed
        assert len(set(validator.labels)) == len(validator.labels)  # No duplicates

    def test_test_case_validator_unknown_status_logs_warning(self):
        """Test TestCaseValidator logs warning for unknown status."""
        with patch("ledzephyr.validators.logger.warning") as mock_warning:
            # Arrange
            data = {"key": "TEST-123", "summary": "Test summary", "status": "Unknown Status"}

            # Act
            TestCaseValidator(**data)

            # Assert
            mock_warning.assert_called_once()
            assert "Unexpected test status" in mock_warning.call_args[0][0]


@pytest.mark.unit
class TestMetricsRequestValidator:
    """Test MetricsRequestValidator class."""

    def test_metrics_request_validator_valid_data_succeeds(self):
        """Test MetricsRequestValidator with valid data succeeds."""
        # Arrange
        valid_data = {
            "project_key": "TEST",
            "time_windows": ["7d", "30d"],
            "team_source": "component",
            "include_inactive": False,
        }

        # Act
        validator = MetricsRequestValidator(**valid_data)

        # Assert
        assert validator.project_key == "TEST"
        assert validator.time_windows == ["7d", "30d"]
        assert validator.team_source == "component"
        assert validator.include_inactive is False

    def test_metrics_request_validator_validates_project_key(self):
        """Test MetricsRequestValidator validates project key."""
        # Arrange
        invalid_data = {"project_key": "invalid_key", "time_windows": ["7d"]}

        # Act & Assert
        with pytest.raises(ValidationError):
            MetricsRequestValidator(**invalid_data)

    def test_metrics_request_validator_validates_time_windows(self):
        """Test MetricsRequestValidator validates time windows."""
        # Arrange
        invalid_data = {"project_key": "TEST", "time_windows": ["7d", "invalid_window"]}

        # Act & Assert
        with pytest.raises(ValidationError):
            MetricsRequestValidator(**invalid_data)

    def test_metrics_request_validator_invalid_team_source_raises_error(self):
        """Test MetricsRequestValidator with invalid team source raises error."""
        # Arrange
        invalid_data = {
            "project_key": "TEST",
            "time_windows": ["7d"],
            "team_source": "invalid_source",
        }

        # Act & Assert
        with pytest.raises(ValidationError):
            MetricsRequestValidator(**invalid_data)

    def test_metrics_request_validator_defaults_team_source(self):
        """Test MetricsRequestValidator defaults team source to component."""
        # Arrange
        data = {"project_key": "TEST", "time_windows": ["7d"]}

        # Act
        validator = MetricsRequestValidator(**data)

        # Assert
        assert validator.team_source == "component"


@pytest.mark.unit
class TestInputValidator:
    """Test InputValidator class."""

    def test_input_validator_creation_with_default_level(self):
        """Test InputValidator creation with default validation level."""
        # Act
        validator = InputValidator()

        # Assert
        assert validator.level == ValidationLevel.MODERATE

    def test_input_validator_creation_with_custom_level(self):
        """Test InputValidator creation with custom validation level."""
        # Act
        validator = InputValidator(level=ValidationLevel.STRICT)

        # Assert
        assert validator.level == ValidationLevel.STRICT

    def test_input_validator_validate_project_key_valid_succeeds(self):
        """Test InputValidator validate_project_key with valid key succeeds."""
        # Arrange
        validator = InputValidator()

        # Act
        result = validator.validate_project_key("TEST")

        # Assert
        assert result.valid is True
        assert result.value == "TEST"

    def test_input_validator_validate_project_key_invalid_fails(self):
        """Test InputValidator validate_project_key with invalid key fails."""
        # Arrange
        validator = InputValidator()

        # Act - Use a key that will still be invalid after uppercasing
        result = validator.validate_project_key("1nvalid")  # Starts with number

        # Assert
        assert result.valid is False
        assert len(result.errors) > 0

    def test_input_validator_validate_email_valid_succeeds(self):
        """Test InputValidator validate_email with valid email succeeds."""
        # Arrange
        validator = InputValidator()

        # Act
        result = validator.validate_email("test@example.com")

        # Assert
        assert result.valid is True
        assert result.value == "test@example.com"

    def test_input_validator_validate_url_valid_succeeds(self):
        """Test InputValidator validate_url with valid URL succeeds."""
        # Arrange
        validator = InputValidator()

        # Act
        result = validator.validate_url("https://example.com")

        # Assert
        assert result.valid is True
        assert result.value == "https://example.com"

    def test_input_validator_validate_api_response_valid_succeeds(self):
        """Test InputValidator validate_api_response with valid data succeeds."""
        # Arrange
        validator = InputValidator()
        data = {"field1": "value1", "field2": "value2"}
        expected_fields = ["field1", "field2"]

        # Act
        result = validator.validate_api_response(data, expected_fields)

        # Assert
        assert result.valid is True
        assert "field1" in result.value
        assert "field2" in result.value


@pytest.mark.unit
class TestGetValidator:
    """Test get_validator function."""

    def test_get_validator_returns_singleton_instance(self):
        """Test get_validator returns singleton instance."""
        # Act
        validator1 = get_validator()
        validator2 = get_validator()

        # Assert
        assert validator1 is validator2

    def test_get_validator_with_different_level_creates_new_instance(self):
        """Test get_validator with different level creates new instance."""
        # Act
        validator1 = get_validator(ValidationLevel.STRICT)
        validator2 = get_validator(ValidationLevel.LENIENT)

        # Assert
        assert validator1 is not validator2
        assert validator1.level == ValidationLevel.STRICT
        assert validator2.level == ValidationLevel.LENIENT

    def test_get_validator_with_same_level_returns_same_instance(self):
        """Test get_validator with same level returns same instance."""
        # Act
        validator1 = get_validator(ValidationLevel.STRICT)
        validator2 = get_validator(ValidationLevel.STRICT)

        # Assert
        assert validator1 is validator2
