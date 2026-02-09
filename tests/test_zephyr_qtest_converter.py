"""Tests for Zephyr ↔ qTest converter module."""

import pytest
from datetime import datetime
from ledzephyr.converters import (
    ZephyrToQtestConverter,
    QtestToZephyrConverter,
)


class TestZephyrToQtestConversion:
    """Test Zephyr → qTest conversion."""

    def test_basic_field_mapping(self):
        """Test basic field mapping from Zephyr to qTest."""
        zephyr_case = {
            "key": "ZEP-123",
            "name": "Login Test",
            "status": "Approved",
            "created_on": "2025-01-01T10:00:00Z",
            "owner": "alice@example.com",
        }

        result = ZephyrToQtestConverter.convert(zephyr_case)

        assert result["test_id"] == "ZEP-123"
        assert result["name"] == "Login Test"
        assert result["status"] == "Active"
        assert result["owner_id"] == "alice@example.com"
        assert "last_modified_date" in result

    def test_status_translation(self):
        """Test status values are correctly translated."""
        assert (
            ZephyrToQtestConverter.convert({"status": "Approved"})["status"]
            == "Active"
        )
        assert (
            ZephyrToQtestConverter.convert({"status": "Draft"})["status"] == "Inactive"
        )
        assert (
            ZephyrToQtestConverter.convert({"status": "Deprecated"})["status"]
            == "Deprecated"
        )

    def test_preserves_description(self):
        """Test description is preserved."""
        zephyr_case = {"name": "Test", "description": "Test description"}
        result = ZephyrToQtestConverter.convert(zephyr_case)
        assert result["description"] == "Test description"

    def test_preserves_custom_fields(self):
        """Test custom fields are preserved."""
        zephyr_case = {
            "name": "Test",
            "custom_fields": {"priority": "high", "component": "auth"},
        }
        result = ZephyrToQtestConverter.convert(zephyr_case)
        assert result["custom_fields"]["priority"] == "high"

    def test_preserves_attachments(self):
        """Test attachments are preserved."""
        attachments = [{"name": "screenshot.png", "size": 1024}]
        zephyr_case = {"name": "Test", "attachments": attachments}
        result = ZephyrToQtestConverter.convert(zephyr_case)
        assert result["attachments"] == attachments

    def test_batch_conversion(self):
        """Test batch conversion of multiple cases."""
        cases = [
            {"key": "ZEP-1", "name": "Test 1", "status": "Approved"},
            {"key": "ZEP-2", "name": "Test 2", "status": "Draft"},
        ]
        results = ZephyrToQtestConverter.convert_batch(cases)
        assert len(results) == 2
        assert results[0]["test_id"] == "ZEP-1"
        assert results[1]["status"] == "Inactive"

    def test_unicode_preservation(self):
        """Test unicode characters are preserved."""
        zephyr_case = {"name": "Test 🎯", "description": "Café résumé"}
        result = ZephyrToQtestConverter.convert(zephyr_case)
        assert result["name"] == "Test 🎯"
        assert result["description"] == "Café résumé"

    def test_null_fields_ignored(self):
        """Test null/missing fields are handled gracefully."""
        zephyr_case = {"key": "ZEP-1", "name": "Test"}
        result = ZephyrToQtestConverter.convert(zephyr_case)
        assert "owner_id" not in result
        assert "status" not in result


class TestQtestToZephyrConversion:
    """Test qTest → Zephyr conversion."""

    def test_basic_field_mapping(self):
        """Test basic field mapping from qTest to Zephyr."""
        qtest_case = {
            "test_id": "QT-456",
            "name": "API Test",
            "status": "Active",
            "last_modified_date": "2025-02-01T10:00:00Z",
            "owner_id": "bob@example.com",
        }

        result = QtestToZephyrConverter.convert(qtest_case)

        assert result["key"] == "QT-456"
        assert result["name"] == "API Test"
        assert result["status"] == "Approved"
        assert result["owner"] == "bob@example.com"
        assert "created_on" in result

    def test_status_translation(self):
        """Test status values are correctly reversed."""
        assert (
            QtestToZephyrConverter.convert({"status": "Active"})["status"]
            == "Approved"
        )
        assert (
            QtestToZephyrConverter.convert({"status": "Inactive"})["status"] == "Draft"
        )
        assert (
            QtestToZephyrConverter.convert({"status": "Deprecated"})["status"]
            == "Deprecated"
        )

    def test_round_trip_fidelity_zephyr_to_qtest_to_zephyr(self):
        """Test round-trip conversion preserves all data."""
        original = {
            "key": "ZEP-789",
            "name": "Round Trip Test",
            "status": "Approved",
            "owner": "charlie@example.com",
            "description": "Test description",
            "custom_fields": {"priority": "medium"},
            "attachments": [{"name": "file.txt", "size": 512}],
        }

        # Zephyr → qTest
        qtest = ZephyrToQtestConverter.convert(original)

        # qTest → Zephyr
        restored = QtestToZephyrConverter.convert(qtest)

        # Verify key fields match
        assert restored["key"] == original["key"]
        assert restored["name"] == original["name"]
        assert restored["status"] == original["status"]
        assert restored["owner"] == original["owner"]
        assert restored["description"] == original["description"]
        assert restored["custom_fields"] == original["custom_fields"]
        assert restored["attachments"] == original["attachments"]

    def test_round_trip_fidelity_qtest_to_zephyr_to_qtest(self):
        """Test reverse round-trip conversion preserves all data."""
        original = {
            "test_id": "QT-111",
            "name": "Reverse Round Trip",
            "status": "Active",
            "owner_id": "dave@example.com",
            "description": "API test description",
            "custom_fields": {"severity": "high"},
            "attachments": [{"name": "response.json", "size": 2048}],
        }

        # qTest → Zephyr
        zephyr = QtestToZephyrConverter.convert(original)

        # Zephyr → qTest
        restored = ZephyrToQtestConverter.convert(zephyr)

        # Verify key fields match
        assert restored["test_id"] == original["test_id"]
        assert restored["name"] == original["name"]
        assert restored["status"] == original["status"]
        assert restored["owner_id"] == original["owner_id"]
        assert restored["description"] == original["description"]
        assert restored["custom_fields"] == original["custom_fields"]
        assert restored["attachments"] == original["attachments"]

    def test_batch_conversion(self):
        """Test batch conversion of multiple cases."""
        cases = [
            {"test_id": "QT-1", "name": "Test 1", "status": "Active"},
            {"test_id": "QT-2", "name": "Test 2", "status": "Inactive"},
        ]
        results = QtestToZephyrConverter.convert_batch(cases)
        assert len(results) == 2
        assert results[0]["key"] == "QT-1"
        assert results[1]["status"] == "Draft"

    def test_unicode_preservation(self):
        """Test unicode characters are preserved in reverse conversion."""
        qtest_case = {"name": "Test 🚀", "description": "Über test"}
        result = QtestToZephyrConverter.convert(qtest_case)
        assert result["name"] == "Test 🚀"
        assert result["description"] == "Über test"

    def test_null_fields_ignored(self):
        """Test null/missing fields are handled gracefully."""
        qtest_case = {"test_id": "QT-1", "name": "Test"}
        result = QtestToZephyrConverter.convert(qtest_case)
        assert "owner" not in result
        assert "status" not in result


class TestConversionEdgeCases:
    """Test edge cases in conversion."""

    def test_empty_custom_fields(self):
        """Test empty custom fields dict."""
        case = {"name": "Test", "custom_fields": {}}
        result = ZephyrToQtestConverter.convert(case)
        assert result["custom_fields"] == {}

    def test_large_batch_conversion(self):
        """Test conversion of large batch (scalability)."""
        cases = [
            {"key": f"ZEP-{i}", "name": f"Test {i}", "status": "Approved"}
            for i in range(1000)
        ]
        results = ZephyrToQtestConverter.convert_batch(cases)
        assert len(results) == 1000
        assert results[999]["test_id"] == "ZEP-999"

    def test_special_characters_in_fields(self):
        """Test special characters in various fields."""
        case = {
            "key": "ZEP-123",
            "name": "Test: Data & Validation",
            "description": "Test\nWith\nNewlines",
        }
        result = ZephyrToQtestConverter.convert(case)
        assert "Data & Validation" in result["name"]
        assert "With" in result["description"]

    def test_iso8601_date_handling(self):
        """Test ISO 8601 date format preservation."""
        case = {"created_on": "2025-02-09T15:30:45.123456Z"}
        result = ZephyrToQtestConverter.convert(case)
        assert "2025-02-09" in result["last_modified_date"]

    def test_unknown_status_passthrough(self):
        """Test unknown status values are passed through unchanged."""
        result = ZephyrToQtestConverter.convert({"status": "UnknownStatus"})
        assert result["status"] == "UnknownStatus"
