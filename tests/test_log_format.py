#!/usr/bin/env python3
"""
Test log format validation against JSON schema.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator, ValidationError, validate

# Log schema definition
LOG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["ts", "level", "msg", "svc", "pid", "tid"],
    "properties": {
        "ts": {
            "type": "string",
            "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\\.[0-9]{3})?Z$",
            "description": "UTC ISO-8601 timestamp",
        },
        "level": {
            "type": "string",
            "enum": ["debug", "info", "notice", "warning", "err", "crit", "alert", "emerg"],
            "description": "RFC 5424 severity level",
        },
        "msg": {"type": "string", "description": "Log message"},
        "svc": {"type": "string", "description": "Service name"},
        "pid": {"type": "integer", "description": "Process ID"},
        "tid": {"type": ["integer", "string"], "description": "Thread ID"},
        "trace_id": {
            "type": "string",
            "pattern": "^[0-9a-f]{32}$",
            "description": "OpenTelemetry trace ID",
        },
        "span_id": {
            "type": "string",
            "pattern": "^[0-9a-f]{16}$",
            "description": "OpenTelemetry span ID",
        },
        "elapsed_ms": {
            "type": "number",
            "minimum": 0,
            "description": "Elapsed time in milliseconds",
        },
        "service.name": {
            "type": "string",
            "description": "OpenTelemetry semantic convention for service name",
        },
        "thread.id": {
            "type": ["integer", "string"],
            "description": "OpenTelemetry semantic convention for thread ID",
        },
    },
    "additionalProperties": True,
}


class TestLogFormat:
    """Test log format validation."""

    def test_valid_minimal_log(self):
        """Test minimal valid log entry."""
        log = {
            "ts": "2025-01-01T00:00:00.000Z",
            "level": "info",
            "msg": "Test message",
            "svc": "workerA",
            "pid": 1234,
            "tid": 5678,
        }
        validate(instance=log, schema=LOG_SCHEMA)

    def test_valid_complete_log(self):
        """Test complete log entry with all optional fields."""
        log = {
            "ts": "2025-01-01T00:00:00.000Z",
            "level": "debug",
            "msg": "Processing request",
            "svc": "api-gateway",
            "pid": 1234,
            "tid": "thread-5678",
            "trace_id": "0123456789abcdef0123456789abcdef",
            "span_id": "0123456789abcdef",
            "elapsed_ms": 123.45,
            "service.name": "api-gateway",
            "thread.id": "thread-5678",
            "extra_field": "allowed",
        }
        validate(instance=log, schema=LOG_SCHEMA)

    def test_all_valid_levels(self):
        """Test all RFC 5424 severity levels."""
        valid_levels = ["debug", "info", "notice", "warning", "err", "crit", "alert", "emerg"]

        for level in valid_levels:
            log = {
                "ts": "2025-01-01T00:00:00Z",
                "level": level,
                "msg": f"Test {level}",
                "svc": "test",
                "pid": 1,
                "tid": 1,
            }
            validate(instance=log, schema=LOG_SCHEMA)

    def test_invalid_level(self):
        """Test invalid severity level."""
        log = {
            "ts": "2025-01-01T00:00:00Z",
            "level": "trace",  # Not in RFC 5424
            "msg": "Test",
            "svc": "test",
            "pid": 1,
            "tid": 1,
        }

        with pytest.raises(ValidationError) as exc_info:
            validate(instance=log, schema=LOG_SCHEMA)
        assert "'trace' is not one of" in str(exc_info.value)

    def test_timestamp_formats(self):
        """Test various ISO-8601 timestamp formats."""
        valid_timestamps = [
            "2025-01-01T00:00:00Z",
            "2025-01-01T00:00:00.000Z",
            "2025-12-31T23:59:59.999Z",
        ]

        for ts in valid_timestamps:
            log = {"ts": ts, "level": "info", "msg": "Test", "svc": "test", "pid": 1, "tid": 1}
            validate(instance=log, schema=LOG_SCHEMA)

    def test_invalid_timestamp(self):
        """Test invalid timestamp format."""
        invalid_timestamps = [
            "2025-01-01 00:00:00",  # Missing T
            "2025-01-01T00:00:00",  # Missing Z
            "2025-01-01T00:00:00+00:00",  # Not UTC Z format
            "01/01/2025 00:00:00",  # Wrong format
        ]

        for ts in invalid_timestamps:
            log = {"ts": ts, "level": "info", "msg": "Test", "svc": "test", "pid": 1, "tid": 1}

            with pytest.raises(ValidationError):
                validate(instance=log, schema=LOG_SCHEMA)

    def test_missing_required_fields(self):
        """Test missing required fields."""
        required_fields = ["ts", "level", "msg", "svc", "pid", "tid"]

        base_log = {
            "ts": "2025-01-01T00:00:00Z",
            "level": "info",
            "msg": "Test",
            "svc": "test",
            "pid": 1,
            "tid": 1,
        }

        for field in required_fields:
            log = base_log.copy()
            del log[field]

            with pytest.raises(ValidationError) as exc_info:
                validate(instance=log, schema=LOG_SCHEMA)
            assert f"'{field}' is a required property" in str(exc_info.value)

    def test_trace_id_format(self):
        """Test OpenTelemetry trace ID format."""
        valid_trace_ids = [
            "0123456789abcdef0123456789abcdef",
            "00000000000000000000000000000000",
            "ffffffffffffffffffffffffffffffff",
        ]

        for trace_id in valid_trace_ids:
            log = {
                "ts": "2025-01-01T00:00:00Z",
                "level": "info",
                "msg": "Test",
                "svc": "test",
                "pid": 1,
                "tid": 1,
                "trace_id": trace_id,
            }
            validate(instance=log, schema=LOG_SCHEMA)

        # Test invalid trace ID
        log["trace_id"] = "invalid"
        with pytest.raises(ValidationError):
            validate(instance=log, schema=LOG_SCHEMA)

    def test_span_id_format(self):
        """Test OpenTelemetry span ID format."""
        valid_span_ids = ["0123456789abcdef", "0000000000000000", "ffffffffffffffff"]

        for span_id in valid_span_ids:
            log = {
                "ts": "2025-01-01T00:00:00Z",
                "level": "info",
                "msg": "Test",
                "svc": "test",
                "pid": 1,
                "tid": 1,
                "span_id": span_id,
            }
            validate(instance=log, schema=LOG_SCHEMA)

    def test_elapsed_ms_numeric(self):
        """Test elapsed_ms is numeric and non-negative."""
        valid_values = [0, 0.1, 123, 123.45, 999999]

        for elapsed in valid_values:
            log = {
                "ts": "2025-01-01T00:00:00Z",
                "level": "info",
                "msg": "Test",
                "svc": "test",
                "pid": 1,
                "tid": 1,
                "elapsed_ms": elapsed,
            }
            validate(instance=log, schema=LOG_SCHEMA)

        # Test negative value
        log["elapsed_ms"] = -1
        with pytest.raises(ValidationError):
            validate(instance=log, schema=LOG_SCHEMA)


def test_sample_logs():
    """Test sample log files against schema."""
    sample_dir = Path("testdata/logs")

    if not sample_dir.exists():
        pytest.skip("Sample logs directory not found")

    validator = Draft7Validator(LOG_SCHEMA)

    for log_file in sample_dir.glob("**/*.log.jsonl"):
        with open(log_file) as f:
            for line_num, line in enumerate(f, 1):
                try:
                    log_entry = json.loads(line)
                    validator.validate(log_entry)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in {log_file}:{line_num}: {e}")
                except ValidationError as e:
                    pytest.fail(f"Schema validation failed in {log_file}:{line_num}: {e.message}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
