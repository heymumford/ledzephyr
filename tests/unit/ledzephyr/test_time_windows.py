"""Unit tests for time window parsing functionality following AAA pattern."""

import time
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from ledzephyr.time_windows import parse_windows


@pytest.mark.unit
@pytest.mark.time
class TestParseWindows:
    """Test time window parsing functionality."""

    def test_parse_windows_empty_list_returns_empty_list(self) -> None:
        """Test parsing empty window list returns empty list."""
        # Arrange
        windows: list[str] = []
        tz = ZoneInfo("UTC")

        # Act
        result = parse_windows(windows, tz)

        # Assert
        assert result == []

    def test_parse_windows_single_hour_window_returns_correct_range(self) -> None:
        """Test parsing single hour window returns correct time range."""
        # Arrange
        windows = ["1h"]
        tz = ZoneInfo("UTC")
        fixed_time = datetime(2025, 9, 21, 12, 0, 0, tzinfo=tz)
        expected_start = datetime(2025, 9, 21, 11, 0, 0, tzinfo=tz)

        # Act
        result = parse_windows(windows, tz, current_time=fixed_time)

        # Assert
        assert len(result) == 1
        assert result[0]["start"] == expected_start
        assert result[0]["end"] == fixed_time
        assert result[0]["duration"] == "1h"

    def test_parse_windows_single_day_window_returns_correct_range(self) -> None:
        """Test parsing single day window returns correct time range."""
        # Arrange
        windows = ["1d"]
        tz = ZoneInfo("UTC")
        fixed_time = datetime(2025, 9, 21, 12, 0, 0, tzinfo=tz)
        expected_start = datetime(2025, 9, 20, 12, 0, 0, tzinfo=tz)

        # Act
        result = parse_windows(windows, tz, current_time=fixed_time)

        # Assert
        assert len(result) == 1
        assert result[0]["start"] == expected_start
        assert result[0]["end"] == fixed_time
        assert result[0]["duration"] == "1d"

    def test_parse_windows_multiple_hours_calculates_correctly(self) -> None:
        """Test parsing multiple hour windows calculates time ranges correctly."""
        # Arrange
        windows = ["24h"]
        tz = ZoneInfo("UTC")
        fixed_time = datetime(2025, 9, 21, 12, 0, 0, tzinfo=tz)
        expected_start = datetime(2025, 9, 20, 12, 0, 0, tzinfo=tz)

        # Act
        result = parse_windows(windows, tz, current_time=fixed_time)

        # Assert
        assert len(result) == 1
        assert result[0]["start"] == expected_start
        assert result[0]["end"] == fixed_time
        assert result[0]["duration"] == "24h"

    def test_parse_windows_multiple_days_calculates_correctly(self) -> None:
        """Test parsing multiple day windows calculates time ranges correctly."""
        # Arrange
        windows = ["7d"]
        tz = ZoneInfo("UTC")
        fixed_time = datetime(2025, 9, 21, 12, 0, 0, tzinfo=tz)
        expected_start = datetime(2025, 9, 14, 12, 0, 0, tzinfo=tz)

        # Act
        result = parse_windows(windows, tz, current_time=fixed_time)

        # Assert
        assert len(result) == 1
        assert result[0]["start"] == expected_start
        assert result[0]["end"] == fixed_time
        assert result[0]["duration"] == "7d"

    def test_parse_windows_multiple_windows_returns_multiple_ranges(self) -> None:
        """Test parsing multiple windows returns multiple time ranges."""
        # Arrange
        windows = ["1h", "24h", "7d"]
        tz = ZoneInfo("UTC")
        fixed_time = datetime(2025, 9, 21, 12, 0, 0, tzinfo=tz)

        # Act
        result = parse_windows(windows, tz, current_time=fixed_time)

        # Assert
        assert len(result) == 3
        # Check 1h window
        assert result[0]["start"] == datetime(2025, 9, 21, 11, 0, 0, tzinfo=tz)
        assert result[0]["end"] == fixed_time
        assert result[0]["duration"] == "1h"
        # Check 24h window
        assert result[1]["start"] == datetime(2025, 9, 20, 12, 0, 0, tzinfo=tz)
        assert result[1]["end"] == fixed_time
        assert result[1]["duration"] == "24h"
        # Check 7d window
        assert result[2]["start"] == datetime(2025, 9, 14, 12, 0, 0, tzinfo=tz)
        assert result[2]["end"] == fixed_time
        assert result[2]["duration"] == "7d"


@pytest.mark.unit
@pytest.mark.timezone
class TestParseWindowsTimezone:
    """Test timezone handling in time window parsing."""

    def test_parse_windows_different_timezone_calculates_correctly(self) -> None:
        """Test parsing windows with different timezone calculates correctly."""
        # Arrange
        windows = ["1h"]
        tz = ZoneInfo("America/New_York")
        fixed_time = datetime(2025, 9, 21, 12, 0, 0, tzinfo=tz)
        expected_start = datetime(2025, 9, 21, 11, 0, 0, tzinfo=tz)

        # Act
        result = parse_windows(windows, tz, current_time=fixed_time)

        # Assert
        assert len(result) == 1
        assert result[0]["start"] == expected_start
        assert result[0]["end"] == fixed_time
        assert result[0]["start"].tzinfo == tz
        assert result[0]["end"].tzinfo == tz

    def test_parse_windows_utc_timezone_calculates_correctly(self) -> None:
        """Test parsing windows with UTC timezone calculates correctly."""
        # Arrange
        windows = ["24h"]
        tz = ZoneInfo("UTC")
        fixed_time = datetime(2025, 9, 21, 0, 0, 0, tzinfo=tz)
        expected_start = datetime(2025, 9, 20, 0, 0, 0, tzinfo=tz)

        # Act
        result = parse_windows(windows, tz, current_time=fixed_time)

        # Assert
        assert len(result) == 1
        assert result[0]["start"] == expected_start
        assert result[0]["end"] == fixed_time
        assert result[0]["start"].tzinfo == tz
        assert result[0]["end"].tzinfo == tz

    def test_parse_windows_asia_timezone_calculates_correctly(self) -> None:
        """Test parsing windows with Asia timezone calculates correctly."""
        # Arrange
        windows = ["12h"]
        tz = ZoneInfo("Asia/Tokyo")
        fixed_time = datetime(2025, 9, 21, 15, 30, 45, tzinfo=tz)
        expected_start = datetime(2025, 9, 21, 3, 30, 45, tzinfo=tz)

        # Act
        result = parse_windows(windows, tz, current_time=fixed_time)

        # Assert
        assert len(result) == 1
        assert result[0]["start"] == expected_start
        assert result[0]["end"] == fixed_time
        assert result[0]["start"].tzinfo == tz
        assert result[0]["end"].tzinfo == tz

    def test_parse_windows_no_current_time_uses_system_time(self) -> None:
        """Test parsing windows without current_time uses system time with timezone."""
        # Arrange
        windows = ["1h"]
        tz = ZoneInfo("UTC")
        mock_now = datetime(2025, 9, 21, 12, 0, 0, tzinfo=tz)
        expected_start = datetime(2025, 9, 21, 11, 0, 0, tzinfo=tz)

        # Act
        with patch("ledzephyr.time_windows.datetime") as mock_datetime:
            # Mock the datetime.now method to return our fixed time
            mock_datetime.now.return_value = mock_now
            # Keep the real datetime constructor for other uses
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = parse_windows(windows, tz)

        # Assert
        assert len(result) == 1
        assert result[0]["start"] == expected_start
        assert result[0]["end"] == mock_now
        assert result[0]["duration"] == "1h"
        mock_datetime.now.assert_called_once_with(tz)


@pytest.mark.unit
class TestParseWindowsErrorHandling:
    """Test error handling in time window parsing."""

    def test_parse_windows_invalid_format_no_number_raises_error(self) -> None:
        """Test parsing window with invalid format (no number) raises ValueError."""
        # Arrange
        windows = ["h"]
        tz = ZoneInfo("UTC")

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid time window format: h"):
            parse_windows(windows, tz)

    def test_parse_windows_invalid_format_no_unit_raises_error(self) -> None:
        """Test parsing window with invalid format (no unit) raises ValueError."""
        # Arrange
        windows = ["24"]
        tz = ZoneInfo("UTC")

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid time window format: 24"):
            parse_windows(windows, tz)

    def test_parse_windows_invalid_format_empty_string_raises_error(self) -> None:
        """Test parsing window with empty string raises ValueError."""
        # Arrange
        windows = [""]
        tz = ZoneInfo("UTC")

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid time window format: "):
            parse_windows(windows, tz)

    def test_parse_windows_invalid_format_special_chars_raises_error(self) -> None:
        """Test parsing window with special characters raises ValueError."""
        # Arrange
        windows = ["24@h"]
        tz = ZoneInfo("UTC")

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid time window format: 24@h"):
            parse_windows(windows, tz)

    def test_parse_windows_unsupported_unit_raises_error(self) -> None:
        """Test parsing window with unsupported unit raises ValueError."""
        # Arrange
        windows = ["1w"]  # weeks not supported
        tz = ZoneInfo("UTC")

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported time unit: w"):
            parse_windows(windows, tz)

    def test_parse_windows_unsupported_unit_months_raises_error(self) -> None:
        """Test parsing window with months unit raises ValueError."""
        # Arrange
        windows = ["3m"]  # months not supported
        tz = ZoneInfo("UTC")

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported time unit: m"):
            parse_windows(windows, tz)

    def test_parse_windows_unsupported_unit_years_raises_error(self) -> None:
        """Test parsing window with years unit raises ValueError."""
        # Arrange
        windows = ["1y"]  # years not supported
        tz = ZoneInfo("UTC")

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported time unit: y"):
            parse_windows(windows, tz)


@pytest.mark.unit
@pytest.mark.time
class TestParseWindowsBoundaryConditions:
    """Test boundary conditions in time window parsing."""

    def test_parse_windows_zero_hours_returns_same_time(self) -> None:
        """Test parsing zero hours window returns same start and end time."""
        # Arrange
        windows = ["0h"]
        tz = ZoneInfo("UTC")
        fixed_time = datetime(2025, 9, 21, 12, 0, 0, tzinfo=tz)

        # Act
        result = parse_windows(windows, tz, current_time=fixed_time)

        # Assert
        assert len(result) == 1
        assert result[0]["start"] == fixed_time
        assert result[0]["end"] == fixed_time
        assert result[0]["duration"] == "0h"

    def test_parse_windows_zero_days_returns_same_time(self) -> None:
        """Test parsing zero days window returns same start and end time."""
        # Arrange
        windows = ["0d"]
        tz = ZoneInfo("UTC")
        fixed_time = datetime(2025, 9, 21, 12, 0, 0, tzinfo=tz)

        # Act
        result = parse_windows(windows, tz, current_time=fixed_time)

        # Assert
        assert len(result) == 1
        assert result[0]["start"] == fixed_time
        assert result[0]["end"] == fixed_time
        assert result[0]["duration"] == "0d"

    def test_parse_windows_leap_year_february_29_calculates_correctly(self) -> None:
        """Test parsing windows during leap year February 29th calculates correctly."""
        # Arrange
        windows = ["24h"]
        tz = ZoneInfo("UTC")
        # February 29, 2024 was a leap year
        fixed_time = datetime(2024, 2, 29, 12, 0, 0, tzinfo=tz)
        expected_start = datetime(2024, 2, 28, 12, 0, 0, tzinfo=tz)

        # Act
        result = parse_windows(windows, tz, current_time=fixed_time)

        # Assert
        assert len(result) == 1
        assert result[0]["start"] == expected_start
        assert result[0]["end"] == fixed_time
        assert result[0]["duration"] == "24h"

    def test_parse_windows_leap_year_day_boundary_calculates_correctly(self) -> None:
        """Test parsing windows crossing leap year day boundary calculates correctly."""
        # Arrange
        windows = ["2d"]
        tz = ZoneInfo("UTC")
        # March 1, 2024 - crossing over February 29th
        fixed_time = datetime(2024, 3, 1, 12, 0, 0, tzinfo=tz)
        expected_start = datetime(2024, 2, 28, 12, 0, 0, tzinfo=tz)

        # Act
        result = parse_windows(windows, tz, current_time=fixed_time)

        # Assert
        assert len(result) == 1
        assert result[0]["start"] == expected_start
        assert result[0]["end"] == fixed_time
        assert result[0]["duration"] == "2d"

    def test_parse_windows_year_boundary_calculates_correctly(self) -> None:
        """Test parsing windows crossing year boundary calculates correctly."""
        # Arrange
        windows = ["48h"]
        tz = ZoneInfo("UTC")
        # January 1, 2025 at noon
        fixed_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=tz)
        expected_start = datetime(2024, 12, 30, 12, 0, 0, tzinfo=tz)

        # Act
        result = parse_windows(windows, tz, current_time=fixed_time)

        # Assert
        assert len(result) == 1
        assert result[0]["start"] == expected_start
        assert result[0]["end"] == fixed_time
        assert result[0]["duration"] == "48h"

    def test_parse_windows_daylight_saving_transition_handles_correctly(self) -> None:
        """Test parsing windows during daylight saving transition handles correctly."""
        # Arrange
        windows = ["25h"]  # During DST transition, this tests edge cases
        tz = ZoneInfo("America/New_York")
        # Spring forward date in 2024 (March 10)
        fixed_time = datetime(2024, 3, 11, 12, 0, 0, tzinfo=tz)

        # Act
        result = parse_windows(windows, tz, current_time=fixed_time)

        # Assert
        assert len(result) == 1
        assert result[0]["end"] == fixed_time
        assert result[0]["duration"] == "25h"
        # The start time should be 25 hours before, accounting for DST
        time_diff = result[0]["end"] - result[0]["start"]
        assert time_diff.total_seconds() == 25 * 3600  # 25 hours in seconds

    def test_parse_windows_very_large_hour_value_calculates_correctly(self) -> None:
        """Test parsing windows with very large hour values calculates correctly."""
        # Arrange
        windows = ["8760h"]  # One year in hours
        tz = ZoneInfo("UTC")
        fixed_time = datetime(2025, 9, 21, 12, 0, 0, tzinfo=tz)
        expected_start = datetime(2024, 9, 21, 12, 0, 0, tzinfo=tz)

        # Act
        result = parse_windows(windows, tz, current_time=fixed_time)

        # Assert
        assert len(result) == 1
        assert result[0]["start"] == expected_start
        assert result[0]["end"] == fixed_time
        assert result[0]["duration"] == "8760h"

    def test_parse_windows_very_large_day_value_calculates_correctly(self) -> None:
        """Test parsing windows with very large day values calculates correctly."""
        # Arrange
        windows = ["365d"]  # One year in days
        tz = ZoneInfo("UTC")
        fixed_time = datetime(2025, 9, 21, 12, 0, 0, tzinfo=tz)
        expected_start = datetime(2024, 9, 21, 12, 0, 0, tzinfo=tz)

        # Act
        result = parse_windows(windows, tz, current_time=fixed_time)

        # Assert
        assert len(result) == 1
        assert result[0]["start"] == expected_start
        assert result[0]["end"] == fixed_time
        assert result[0]["duration"] == "365d"


@pytest.mark.unit
@pytest.mark.perf
class TestParseWindowsPerformance:
    """Test performance characteristics of time window parsing."""

    def test_parse_windows_large_number_of_windows_performs_well(self) -> None:
        """Test parsing large number of windows performs within reasonable time."""
        # Arrange
        windows = [f"{i}h" for i in range(1, 101)]  # 100 different hour windows
        tz = ZoneInfo("UTC")
        fixed_time = datetime(2025, 9, 21, 12, 0, 0, tzinfo=tz)

        # Act
        start_time = time.perf_counter()
        result = parse_windows(windows, tz, current_time=fixed_time)
        end_time = time.perf_counter()

        # Assert
        assert len(result) == 100
        assert end_time - start_time < 1.0  # Should complete within 1 second
        # Verify first and last windows are calculated correctly
        assert result[0]["duration"] == "1h"
        assert result[0]["start"] == datetime(2025, 9, 21, 11, 0, 0, tzinfo=tz)
        assert result[-1]["duration"] == "100h"
        expected_last_start = fixed_time - timedelta(hours=100)
        assert result[-1]["start"] == expected_last_start

    def test_parse_windows_large_time_ranges_performs_well(self) -> None:
        """Test parsing windows with large time ranges performs within reasonable time."""
        # Arrange
        windows = ["87600h", "3650d"]  # 10 years in hours and days
        tz = ZoneInfo("UTC")
        fixed_time = datetime(2025, 9, 21, 12, 0, 0, tzinfo=tz)

        # Act
        start_time = time.perf_counter()
        result = parse_windows(windows, tz, current_time=fixed_time)
        end_time = time.perf_counter()

        # Assert
        assert len(result) == 2
        assert end_time - start_time < 0.1  # Should complete very quickly
        assert result[0]["duration"] == "87600h"
        assert result[1]["duration"] == "3650d"

    @pytest.mark.benchmark
    def test_parse_windows_benchmark_single_window(self, benchmark: Any) -> None:
        """Benchmark performance of parsing a single window."""
        # Arrange
        windows = ["24h"]
        tz = ZoneInfo("UTC")
        fixed_time = datetime(2025, 9, 21, 12, 0, 0, tzinfo=tz)

        # Act & Assert
        result = benchmark(parse_windows, windows, tz, fixed_time)
        assert len(result) == 1
        assert result[0]["duration"] == "24h"

    @pytest.mark.benchmark
    def test_parse_windows_benchmark_multiple_windows(self, benchmark: Any) -> None:
        """Benchmark performance of parsing multiple windows."""
        # Arrange
        windows = ["1h", "6h", "24h", "7d", "30d"]
        tz = ZoneInfo("UTC")
        fixed_time = datetime(2025, 9, 21, 12, 0, 0, tzinfo=tz)

        # Act & Assert
        result = benchmark(parse_windows, windows, tz, fixed_time)
        assert len(result) == 5
