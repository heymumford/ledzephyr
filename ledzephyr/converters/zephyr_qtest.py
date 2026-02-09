"""
Zephyr ↔ qTest bidirectional test case converter.

Handles conversion between Zephyr and qTest test case formats with
full round-trip fidelity for metadata, attachments, and unicode content.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


# Status mappings between Zephyr and qTest
_ZEPHYR_TO_QTEST_STATUS = {
    "Approved": "Active",
    "Draft": "Inactive",
    "Deprecated": "Deprecated",
}

_QTEST_TO_ZEPHYR_STATUS = {
    "Active": "Approved",
    "Inactive": "Draft",
    "Deprecated": "Deprecated",
}


@dataclass
class Attachment:
    """Represents a test case attachment."""

    name: str
    content: bytes
    size: int


@dataclass
class TestCase:
    """Base test case representation."""

    key: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    created_on: Optional[str] = None
    owner: Optional[str] = None
    description: Optional[str] = None
    attachments: List[Attachment] = None
    custom_fields: Dict[str, Any] = None

    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []
        if self.custom_fields is None:
            self.custom_fields = {}


class ZephyrToQtestConverter:
    """Converts test cases from Zephyr format to qTest format."""

    @staticmethod
    def convert(zephyr_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a Zephyr test case to qTest format.

        Args:
            zephyr_case: Test case dict with Zephyr field names

        Returns:
            Test case dict with qTest field names
        """
        qtest_case = {}

        # Field mapping
        if "key" in zephyr_case:
            qtest_case["test_id"] = zephyr_case["key"]
        if "name" in zephyr_case:
            qtest_case["name"] = zephyr_case["name"]
        if "status" in zephyr_case:
            qtest_case["status"] = _ZEPHYR_TO_QTEST_STATUS.get(
                zephyr_case["status"], zephyr_case["status"]
            )
        if "created_on" in zephyr_case:
            qtest_case["last_modified_date"] = _parse_date(zephyr_case["created_on"])
        if "owner" in zephyr_case:
            qtest_case["owner_id"] = zephyr_case["owner"]
        if "description" in zephyr_case:
            qtest_case["description"] = zephyr_case["description"]

        # Preserve custom fields and attachments
        if "custom_fields" in zephyr_case:
            qtest_case["custom_fields"] = zephyr_case["custom_fields"]
        if "attachments" in zephyr_case:
            qtest_case["attachments"] = zephyr_case["attachments"]

        return qtest_case

    @staticmethod
    def convert_batch(zephyr_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert multiple Zephyr test cases to qTest format.

        Args:
            zephyr_cases: List of test case dicts in Zephyr format

        Returns:
            List of test case dicts in qTest format
        """
        return [ZephyrToQtestConverter.convert(case) for case in zephyr_cases]


class QtestToZephyrConverter:
    """Converts test cases from qTest format to Zephyr format."""

    @staticmethod
    def convert(qtest_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a qTest test case to Zephyr format.

        Args:
            qtest_case: Test case dict with qTest field names

        Returns:
            Test case dict with Zephyr field names
        """
        zephyr_case = {}

        # Field mapping (reverse of ZephyrToQtest)
        if "test_id" in qtest_case:
            zephyr_case["key"] = qtest_case["test_id"]
        if "name" in qtest_case:
            zephyr_case["name"] = qtest_case["name"]
        if "status" in qtest_case:
            zephyr_case["status"] = _QTEST_TO_ZEPHYR_STATUS.get(
                qtest_case["status"], qtest_case["status"]
            )
        if "last_modified_date" in qtest_case:
            zephyr_case["created_on"] = _format_date(qtest_case["last_modified_date"])
        if "owner_id" in qtest_case:
            zephyr_case["owner"] = qtest_case["owner_id"]
        if "description" in qtest_case:
            zephyr_case["description"] = qtest_case["description"]

        # Preserve custom fields and attachments
        if "custom_fields" in qtest_case:
            zephyr_case["custom_fields"] = qtest_case["custom_fields"]
        if "attachments" in qtest_case:
            zephyr_case["attachments"] = qtest_case["attachments"]

        return zephyr_case

    @staticmethod
    def convert_batch(qtest_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert multiple qTest test cases to Zephyr format.

        Args:
            qtest_cases: List of test case dicts in qTest format

        Returns:
            List of test case dicts in Zephyr format
        """
        return [QtestToZephyrConverter.convert(case) for case in qtest_cases]


def _parse_date(date_str: str) -> str:
    """Parse and normalize date to ISO 8601 format."""
    if not date_str:
        return None
    # Handle various date formats, default to ISO 8601
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.isoformat()
    except (ValueError, AttributeError):
        return date_str


def _format_date(date_obj: Any) -> str:
    """Format date to ISO 8601 string."""
    if not date_obj:
        return None
    if isinstance(date_obj, str):
        return _parse_date(date_obj)
    if isinstance(date_obj, datetime):
        return date_obj.isoformat()
    return str(date_obj)
