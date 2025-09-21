"""Simple unit tests to improve coverage."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from ledzephyr.time_windows import parse_windows


@pytest.mark.unit
class TestTimeWindows:
    """Test time window parsing."""

    def test_parse_windows_basic(self):
        """Test basic window parsing."""
        # Test with valid time windows
        tz = ZoneInfo("UTC")
        windows = ["24h", "7d"]
        result = parse_windows(windows, tz)
        assert result is not None
        assert len(result) == 2
        assert result[0]["duration"] == "24h"
        assert result[1]["duration"] == "7d"

    def test_parse_windows_empty(self):
        """Test parsing empty windows."""
        tz = ZoneInfo("UTC")
        result = parse_windows([], tz)
        assert result is not None
        assert len(result) == 0

    def test_parse_windows_single_hour(self):
        """Test parsing single hour window."""
        tz = ZoneInfo("UTC")
        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=tz)
        windows = ["1h"]
        result = parse_windows(windows, tz, current_time=now)
        assert result is not None
        assert len(result) == 1
        assert result[0]["duration"] == "1h"
        # Check that the window is 1 hour
        delta = result[0]["end"] - result[0]["start"]
        assert delta.total_seconds() == 3600

    def test_parse_windows_invalid_format(self):
        """Test parsing invalid window format."""
        tz = ZoneInfo("UTC")
        with pytest.raises(ValueError, match="Invalid time window format"):
            parse_windows(["invalid"], tz)

    def test_parse_windows_unsupported_unit(self):
        """Test parsing unsupported time unit."""
        tz = ZoneInfo("UTC")
        with pytest.raises(ValueError, match="Unsupported time unit"):
            parse_windows(["5m"], tz)  # minutes not supported
