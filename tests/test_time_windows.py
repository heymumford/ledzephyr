"""Tests for time windows parsing functionality."""

import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from ledzephyr.time_windows import parse_windows


def test_parse_windows_24h():
    """Test parsing of 24h window."""
    tz = ZoneInfo("UTC")
    now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=tz)
    
    result = parse_windows(["24h"], tz, current_time=now)
    assert len(result) == 1
    window = result[0]
    
    expected_start = now - timedelta(hours=24)
    expected_end = now
    
    assert window["start"] == expected_start
    assert window["end"] == expected_end
    assert window["duration"] == "24h"


def test_parse_windows_7d():
    """Test parsing of 7d window."""
    tz = ZoneInfo("UTC")
    now = datetime(2024, 1, 15, 12, 30, 45, tzinfo=tz)
    
    result = parse_windows(["7d"], tz, current_time=now)
    assert len(result) == 1
    window = result[0]
    
    expected_start = now - timedelta(days=7)
    expected_end = now
    
    assert window["start"] == expected_start
    assert window["end"] == expected_end
    assert window["duration"] == "7d"


def test_parse_windows_multiple():
    """Test parsing multiple time windows."""
    tz = ZoneInfo("America/New_York")
    now = datetime(2024, 6, 15, 14, 25, 30, tzinfo=tz)
    
    result = parse_windows(["24h", "7d"], tz, current_time=now)
    assert len(result) == 2
    
    # Check 24h window
    window_24h = result[0]
    assert window_24h["duration"] == "24h"
    assert window_24h["start"] == now - timedelta(hours=24)
    assert window_24h["end"] == now
    
    # Check 7d window
    window_7d = result[1]
    assert window_7d["duration"] == "7d"
    assert window_7d["start"] == now - timedelta(days=7)
    assert window_7d["end"] == now


def test_parse_windows_timezone_aware():
    """Test that windows are timezone aware with second precision."""
    tz = ZoneInfo("Europe/London")
    now = datetime(2024, 7, 10, 9, 15, 23, tzinfo=tz)
    
    result = parse_windows(["24h"], tz, current_time=now)
    window = result[0]
    
    # Check timezone info is preserved
    assert window["start"].tzinfo == tz
    assert window["end"].tzinfo == tz
    
    # Check second precision (microseconds should be preserved)
    assert window["end"].second == 23
    assert window["start"].second == 23


def test_parse_windows_invalid_format():
    """Test parsing with invalid time window format."""
    tz = ZoneInfo("UTC")
    
    with pytest.raises(ValueError, match="Invalid time window format"):
        parse_windows(["invalid"], tz)


def test_parse_windows_empty_list():
    """Test parsing with empty window list."""
    tz = ZoneInfo("UTC")
    result = parse_windows([], tz)
    assert result == []


def test_parse_windows_unsupported_unit():
    """Test parsing with unsupported time unit."""
    tz = ZoneInfo("UTC")
    
    with pytest.raises(ValueError, match="Unsupported time unit"):
        parse_windows(["5m"], tz)