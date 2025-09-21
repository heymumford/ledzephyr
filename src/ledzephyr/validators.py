"""
Data validation and sanitization for ledzephyr.

Provides comprehensive input validation, data sanitization,
and security checks for all user inputs and API responses.
"""

import html
import logging
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
from typing import Annotated, Any, Generic, TypeVar

from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ValidationLevel(Enum):
    """Validation strictness levels."""

    STRICT = "strict"  # Fail on any validation error
    MODERATE = "moderate"  # Sanitize and warn
    LENIENT = "lenient"  # Sanitize silently


@dataclass
class ValidationResult(Generic[T]):
    """Result of a validation operation."""

    valid: bool
    value: T | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sanitized: bool = False


class ProjectKeyValidator(BaseModel):
    """Validator for Jira project keys."""

    key: Annotated[
        str, StringConstraints(pattern=r"^[A-Z][A-Z0-9]{1,9}$", min_length=2, max_length=10)
    ]

    @field_validator("key")
    @classmethod
    def validate_project_key(cls, v):
        """Validate project key format."""
        if not v or not v.isupper():
            raise ValueError("Project key must be uppercase")
        if v in ["TEST", "DEMO", "TEMP"]:
            logger.warning(f"Using test project key: {v}")
        return v


class TimeWindowValidator(BaseModel):
    """Validator for time window specifications."""

    window: str

    @field_validator("window")
    @classmethod
    def validate_time_window(cls, v):
        """Validate time window format (e.g., '7d', '24h', '30d')."""
        pattern = r"^(\d+)([hdwmHDWM])$"
        match = re.match(pattern, v)

        if not match:
            raise ValueError("Invalid time window format. Use format like '7d', '24h', '30d'")

        value, unit = match.groups()
        value = int(value)
        unit = unit.lower()

        # Validate that value is not zero
        if value == 0:
            raise ValueError("Time window value cannot be zero")

        # Validate reasonable ranges
        if unit == "h" and value > 744:  # 31 days in hours
            raise ValueError("Hour window cannot exceed 744 hours (31 days)")
        elif unit == "d" and value > 365:
            raise ValueError("Day window cannot exceed 365 days")
        elif unit == "w" and value > 52:
            raise ValueError("Week window cannot exceed 52 weeks")
        elif unit == "m" and value > 12:
            raise ValueError("Month window cannot exceed 12 months")

        return v

    def to_timedelta(self) -> timedelta:
        """Convert validated window to timedelta."""
        match = re.match(r"^(\d+)([hdwm])$", self.window.lower())
        value, unit = match.groups()
        value = int(value)

        if unit == "h":
            return timedelta(hours=value)
        elif unit == "d":
            return timedelta(days=value)
        elif unit == "w":
            return timedelta(weeks=value)
        elif unit == "m":
            return timedelta(days=value * 30)  # Approximate


class EmailValidator(BaseModel):
    """Validator for email addresses."""

    email: Annotated[
        str,
        StringConstraints(
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", max_length=254
        ),
    ]

    @field_validator("email")
    @classmethod
    def validate_email_domain(cls, v):
        """Additional email validation."""
        domain = v.split("@")[1]

        # Check for consecutive dots in domain
        if ".." in domain:
            raise ValueError("Email domain cannot contain consecutive dots")

        # Check for common typos
        typo_domains = {
            "gmial.com": "gmail.com",
            "gmai.com": "gmail.com",
            "yahooo.com": "yahoo.com",
            "outlok.com": "outlook.com",
        }

        if domain in typo_domains:
            logger.warning(f"Possible typo in email domain: {domain}")
            # Don't auto-correct in strict mode

        return v.lower()  # Normalize to lowercase


class URLValidator(BaseModel):
    """Validator for URLs."""

    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        """Validate and sanitize URL."""
        # Basic URL validation
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
            r"localhost|"  # localhost...
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

        if not url_pattern.match(v):
            raise ValueError(f"Invalid URL format: {v}")

        # Parse and validate components
        parsed = urllib.parse.urlparse(v)

        # Ensure HTTPS for production URLs
        if "atlassian.net" in parsed.netloc and parsed.scheme != "https":
            raise ValueError("Atlassian URLs must use HTTPS")

        # Remove trailing slashes
        if v.endswith("/"):
            v = v.rstrip("/")

        return v


class APITokenValidator(BaseModel):
    """Validator for API tokens."""

    token: Annotated[str, StringConstraints(min_length=20, max_length=500)]

    @field_validator("token")
    @classmethod
    def validate_token(cls, v):
        """Validate API token format."""
        # Remove common prefixes if present
        prefixes_to_remove = ["Bearer ", "Token ", "Basic "]
        for prefix in prefixes_to_remove:
            if v.startswith(prefix):
                v = v[len(prefix) :]

        # Check for common invalid patterns
        if v == "your-token-here" or v == "xxx":
            raise ValueError("Invalid placeholder token")

        # Warn about tokens that look like they might be exposed
        if " " in v or "\n" in v:
            raise ValueError("Token contains invalid characters")

        return v.strip()


class TestCaseValidator(BaseModel):
    """Validator for test case data."""

    key: Annotated[str, StringConstraints(pattern=r"^[A-Z]{2,10}-\d+$")]
    summary: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    status: str | None = None
    component: str | None = None
    labels: list[str] = Field(default_factory=list)

    @field_validator("summary")
    @classmethod
    def sanitize_summary(cls, v):
        """Sanitize test case summary."""
        # Remove HTML tags
        v = re.sub(r"<[^>]+>", "", v)
        # Escape HTML entities
        v = html.escape(v)
        # Remove excessive whitespace
        v = " ".join(v.split())
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate test case status."""
        if v:
            valid_statuses = [
                "Open",
                "In Progress",
                "Done",
                "Closed",
                "Pass",
                "Fail",
                "Blocked",
                "Not Executed",
            ]
            if v not in valid_statuses:
                logger.warning(f"Unexpected test status: {v}")
        return v

    @field_validator("labels")
    @classmethod
    def sanitize_labels(cls, v):
        """Sanitize and validate labels."""
        sanitized = []
        for label in v:
            # Remove special characters
            label = re.sub(r"[^a-zA-Z0-9_-]", "", label)
            # Limit length
            label = label[:50]
            if label:
                sanitized.append(label.lower())
        return list(set(sanitized))  # Remove duplicates


class MetricsRequestValidator(BaseModel):
    """Validator for metrics API requests."""

    project_key: str
    time_windows: list[str]
    team_source: str | None = "component"
    include_inactive: bool = False

    @field_validator("project_key")
    @classmethod
    def validate_project_key(cls, v):
        """Validate project key."""
        return ProjectKeyValidator.validate_project_key(v)

    @field_validator("time_windows")
    @classmethod
    def validate_time_windows(cls, v):
        """Validate all time windows."""
        validated = []
        for window in v:
            try:
                validator = TimeWindowValidator(window=window)
                validated.append(validator.window)
            except ValidationError as e:
                raise ValueError(f"Invalid time window '{window}': {e}") from e
        return validated

    @field_validator("team_source")
    @classmethod
    def validate_team_source(cls, v):
        """Validate team source."""
        valid_sources = ["component", "label", "assignee", "custom"]
        if v and v.lower() not in valid_sources:
            raise ValueError(f"Invalid team source: {v}")
        return v.lower() if v else "component"


class DataSanitizer:
    """General data sanitization utilities."""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000, allow_html: bool = False) -> str:
        """Sanitize string input."""
        if not value:
            return ""

        # Truncate to max length
        value = value[:max_length]

        # Remove null bytes
        value = value.replace("\x00", "")

        # Escape or remove HTML
        if not allow_html:
            value = html.escape(value)
        else:
            # Allow only safe HTML tags
            allowed_tags = ["b", "i", "u", "strong", "em", "code", "pre"]
            value = DataSanitizer._sanitize_html(value, allowed_tags)

        # Normalize whitespace
        value = " ".join(value.split())

        return value

    @staticmethod
    def _sanitize_html(html_string: str, allowed_tags: list[str]) -> str:
        """Remove all HTML tags except allowed ones."""
        # Simple implementation - in production use bleach or similar
        pattern = r"<(?!/?(?:" + "|".join(allowed_tags) + r")\b)[^>]+>"
        return re.sub(pattern, "", html_string)

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe file operations."""
        # Remove path components
        filename = filename.replace("/", "").replace("\\", "")

        # Remove special characters
        filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)

        # Limit length
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        if ext:
            filename = f"{name[:200]}.{ext[:10]}"
        else:
            filename = name[:200]

        # Prevent directory traversal
        if filename.startswith("."):
            filename = "_" + filename[1:]

        # Remove any ".." patterns that could be used for directory traversal
        while ".." in filename:
            filename = filename.replace("..", "_")

        return filename

    @staticmethod
    def sanitize_sql_identifier(identifier: str) -> str:
        """Sanitize SQL identifiers to prevent injection."""
        # Only allow alphanumeric and underscore
        return re.sub(r"[^a-zA-Z0-9_]", "", identifier)[:64]

    @staticmethod
    def sanitize_json_data(data: Any) -> Any:
        """Recursively sanitize JSON-like data structures."""
        if isinstance(data, dict):
            return {
                DataSanitizer.sanitize_string(k, 100): DataSanitizer.sanitize_json_data(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [DataSanitizer.sanitize_json_data(item) for item in data]
        elif isinstance(data, str):
            return DataSanitizer.sanitize_string(data)
        else:
            return data


class InputValidator:
    """Main input validation manager."""

    def __init__(self, level: ValidationLevel = ValidationLevel.MODERATE):
        self.level = level
        self.sanitizer = DataSanitizer()

    def validate_project_key(self, key: str) -> ValidationResult[str]:
        """Validate a project key."""
        result = ValidationResult[str](valid=False)

        try:
            validator = ProjectKeyValidator(key=key.upper())
            result.valid = True
            result.value = validator.key
        except ValidationError as e:
            result.errors = [str(err) for err in e.errors()]

            if self.level == ValidationLevel.LENIENT:
                # Try to sanitize
                sanitized = re.sub(r"[^A-Z0-9]", "", key.upper())[:10]
                if len(sanitized) >= 2:
                    result.value = sanitized
                    result.sanitized = True
                    result.warnings.append(f"Project key sanitized: {key} -> {sanitized}")

        return result

    def validate_email(self, email: str) -> ValidationResult[str]:
        """Validate an email address."""
        result = ValidationResult[str](valid=False)

        try:
            validator = EmailValidator(email=email)
            result.valid = True
            result.value = validator.email
        except ValidationError as e:
            result.errors = [str(err) for err in e.errors()]

            if self.level != ValidationLevel.STRICT:
                # Try basic sanitization
                sanitized = email.strip().lower()
                if "@" in sanitized:
                    result.value = sanitized
                    result.sanitized = True
                    result.warnings.append("Email format may be invalid")

        return result

    def validate_url(self, url: str) -> ValidationResult[str]:
        """Validate a URL."""
        result = ValidationResult[str](valid=False)

        try:
            validator = URLValidator(url=url)
            result.valid = True
            result.value = validator.url
        except ValidationError as e:
            result.errors = [str(err) for err in e.errors()]

            if self.level == ValidationLevel.LENIENT:
                # Try to fix common issues
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                result.value = url
                result.sanitized = True
                result.warnings.append("URL format adjusted")

        return result

    def validate_api_response(
        self, data: dict[str, Any], expected_fields: list[str]
    ) -> ValidationResult[dict[str, Any]]:
        """Validate API response data."""
        result = ValidationResult[dict[str, Any]](valid=True)
        result.value = {}

        # Check for required fields
        missing_fields = [field for field in expected_fields if field not in data]

        if missing_fields:
            result.warnings.append(f"Missing expected fields: {', '.join(missing_fields)}")
            if self.level == ValidationLevel.STRICT:
                result.valid = False
                result.errors.append("Required fields missing")
                return result

        # Sanitize all string fields
        for key, value in data.items():
            if isinstance(value, str):
                result.value[key] = self.sanitizer.sanitize_string(value)
            else:
                result.value[key] = self.sanitizer.sanitize_json_data(value)

        return result

    def validate_batch(
        self, items: list[dict[str, Any]], validator_class: type
    ) -> list[ValidationResult]:
        """Validate a batch of items."""
        results = []

        for item in items:
            result = ValidationResult[dict[str, Any]](valid=False)

            try:
                validated = validator_class(**item)
                result.valid = True
                result.value = validated.dict()
            except ValidationError as e:
                result.errors = [str(err) for err in e.errors()]

                if self.level != ValidationLevel.STRICT:
                    # Attempt partial validation
                    result.value = self.sanitizer.sanitize_json_data(item)
                    result.sanitized = True
                    result.warnings.append("Item sanitized due to validation errors")

            results.append(result)

        return results


# Global validator instance
_validator: InputValidator | None = None


def get_validator(level: ValidationLevel = ValidationLevel.MODERATE) -> InputValidator:
    """Get global validator instance."""
    global _validator
    if _validator is None or _validator.level != level:
        _validator = InputValidator(level)
    return _validator
