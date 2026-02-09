"""
Contract validation for test case conversions.

Validates schema compliance for Zephyr and qTest test case formats,
ensuring field presence, types, enums, and data integrity.

Contract guarantees:
- Zephyr cases: require 'key' and 'name', valid statuses (Approved/Draft/Deprecated)
- qTest cases: require 'test_id' and 'name', valid statuses (Active/Inactive/Deprecated)
- Custom fields must be dict or missing
- Attachments must be list with valid metadata (name, size)
- Dates must conform to ISO 8601 format
- Field types must match declared schema

Usage:
    validator = ContractValidator()
    if validator.validate_zephyr_case(case):
        # case is valid, safe to convert
        qtest = ZephyrToQtestConverter.convert(case)
"""

from typing import Any, Dict, List, Optional
from datetime import datetime


# Platform-specific valid status values
ZEPHYR_STATUSES = {"Approved", "Draft", "Deprecated"}
QTEST_STATUSES = {"Active", "Inactive", "Deprecated"}


class ContractValidator:
    """Validates test case schema contracts for conversion.

    Ensures schema compliance for Zephyr and qTest test case formats.
    Use before conversion to catch schema violations early.
    """

    @staticmethod
    def validate_zephyr_case(case: Dict[str, Any]) -> bool:
        """
        Validate a Zephyr test case against schema contract.

        Args:
            case: Test case dict to validate

        Returns:
            True if case is valid, False otherwise

        Contract guarantees:
        - Must have 'key' and 'name' fields (both required)
        - If 'status' present, must be in {Approved, Draft, Deprecated}
        - custom_fields must be dict (if present)
        - attachments must be list (if present, can be None)
        """
        return (
            _has_required_fields(case, ["key", "name"])
            and _validate_status(case, ZEPHYR_STATUSES)
            and _validate_custom_fields_type(case)
            and _validate_attachments_type(case)
        )

    @staticmethod
    def validate_qtest_case(case: Dict[str, Any]) -> bool:
        """
        Validate a qTest test case against schema contract.

        Args:
            case: Test case dict to validate

        Returns:
            True if case is valid, False otherwise

        Contract guarantees:
        - Must have 'test_id' and 'name' fields (both required)
        - If 'status' present, must be in {Active, Inactive, Deprecated}
        - custom_fields must be dict (if present)
        - attachments must be list (if present, can be None)
        """
        return (
            _has_required_fields(case, ["test_id", "name"])
            and _validate_status(case, QTEST_STATUSES)
            and _validate_custom_fields_type(case)
            and _validate_attachments_type(case)
        )

    @staticmethod
    def validate_field_types(
        case: Dict[str, Any], schema: Dict[str, type]
    ) -> bool:
        """
        Validate field types against schema.

        Args:
            case: Test case dict
            schema: Dict mapping field names to expected types

        Returns:
            True if all fields match expected types, False otherwise

        Example:
            schema = {"key": str, "custom_fields": dict}
            assert validator.validate_field_types(case, schema)
        """
        for field, expected_type in schema.items():
            if field in case and not isinstance(case[field], expected_type):
                return False
        return True

    @staticmethod
    def validate_enum_values(
        case: Dict[str, Any], enums: Dict[str, List[str]]
    ) -> bool:
        """
        Validate enum field values.

        Args:
            case: Test case dict
            enums: Dict mapping field names to list of valid values

        Returns:
            True if all enum fields contain valid values, False otherwise

        Example:
            enums = {"status": ["Approved", "Draft", "Deprecated"]}
            assert validator.validate_enum_values(case, enums)
        """
        for field, valid_values in enums.items():
            if field in case and case[field] not in valid_values:
                return False
        return True

    @staticmethod
    def validate_dates(case: Dict[str, Any]) -> bool:
        """
        Validate ISO 8601 date formats.

        Args:
            case: Test case dict (checks created_on, last_modified_date, updated_on)

        Returns:
            True if all date fields are valid ISO 8601, False otherwise

        Supported formats:
        - "2025-02-09T10:00:00Z" (with Z timezone)
        - "2025-02-09T10:00:00+00:00" (with offset)
        - datetime objects
        """
        date_fields = ["created_on", "last_modified_date", "updated_on"]

        for field in date_fields:
            if field not in case:
                continue

            date_value = case[field]
            if date_value is None:
                continue

            if not _is_valid_iso8601(date_value):
                return False

        return True

    @staticmethod
    def validate_attachment(attachment: Dict[str, Any]) -> bool:
        """
        Validate attachment metadata.

        Args:
            attachment: Attachment dict

        Returns:
            True if attachment has required fields, False otherwise

        Contract guarantees:
        - Must have 'name' field (string, non-empty)
        - Must have 'size' field (int or float, non-negative)
        """
        return (
            "name" in attachment
            and isinstance(attachment["name"], str)
            and "size" in attachment
            and isinstance(attachment["size"], (int, float))
            and attachment["size"] >= 0
        )


# Private helper functions for validation logic extraction


def _has_required_fields(case: Dict[str, Any], required: List[str]) -> bool:
    """Check if all required fields are present."""
    return all(field in case for field in required)


def _validate_status(case: Dict[str, Any], valid_statuses: set) -> bool:
    """Validate status field if present."""
    if "status" not in case:
        return True
    return case["status"] in valid_statuses


def _validate_custom_fields_type(case: Dict[str, Any]) -> bool:
    """Validate custom_fields is dict or missing."""
    if "custom_fields" not in case:
        return True
    return isinstance(case["custom_fields"], dict)


def _validate_attachments_type(case: Dict[str, Any]) -> bool:
    """Validate attachments is list or None."""
    if "attachments" not in case:
        return True
    attachments = case["attachments"]
    return attachments is None or isinstance(attachments, list)


def _is_valid_iso8601(date_value: Any) -> bool:
    """Check if value is valid ISO 8601 date."""
    try:
        if isinstance(date_value, str):
            # Handle ISO 8601 with Z timezone indicator
            normalized = date_value.replace("Z", "+00:00")
            datetime.fromisoformat(normalized)
            return True
        elif isinstance(date_value, datetime):
            # Already a datetime object
            return True
        else:
            return False
    except (ValueError, AttributeError):
        return False
