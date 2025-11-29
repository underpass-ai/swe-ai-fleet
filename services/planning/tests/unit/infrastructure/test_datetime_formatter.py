"""Unit tests for datetime_formatter."""

from datetime import UTC, datetime, timezone, timedelta

import pytest
from planning.infrastructure.mappers.datetime_formatter import format_datetime_iso


def test_format_datetime_iso_naive():
    """Test formatting naive datetime (assumes UTC)."""
    dt = datetime(2025, 11, 28, 12, 30, 45, 123456)
    result = format_datetime_iso(dt)

    assert result == "2025-11-28T12:30:45.123Z"
    assert result.endswith("Z")
    assert "+" not in result
    assert "-" not in result[-6:]  # No timezone offset


def test_format_datetime_iso_utc_aware():
    """Test formatting UTC-aware datetime."""
    dt = datetime(2025, 11, 28, 12, 30, 45, 123456, tzinfo=UTC)
    result = format_datetime_iso(dt)

    assert result == "2025-11-28T12:30:45.123Z"
    assert result.endswith("Z")


def test_format_datetime_iso_other_timezone():
    """Test formatting timezone-aware datetime (converts to UTC)."""
    # Create datetime with +02:00 offset
    tz = timezone(timedelta(hours=2))
    dt = datetime(2025, 11, 28, 14, 30, 45, 123456, tzinfo=tz)
    result = format_datetime_iso(dt)

    # Should convert to UTC (subtract 2 hours)
    assert result == "2025-11-28T12:30:45.123Z"
    assert result.endswith("Z")
    assert "+" not in result


def test_format_datetime_iso_negative_timezone():
    """Test formatting datetime with negative timezone offset."""
    # Create datetime with -05:00 offset
    tz = timezone(timedelta(hours=-5))
    dt = datetime(2025, 11, 28, 7, 30, 45, 123456, tzinfo=tz)
    result = format_datetime_iso(dt)

    # Should convert to UTC (add 5 hours)
    assert result == "2025-11-28T12:30:45.123Z"
    assert result.endswith("Z")


def test_format_datetime_iso_milliseconds():
    """Test formatting with different millisecond precisions."""
    # Test with microseconds
    dt1 = datetime(2025, 11, 28, 12, 30, 45, 123456, tzinfo=UTC)
    result1 = format_datetime_iso(dt1)
    assert result1 == "2025-11-28T12:30:45.123Z"

    # Test with fewer microseconds (should pad with zeros)
    dt2 = datetime(2025, 11, 28, 12, 30, 45, 123000, tzinfo=UTC)
    result2 = format_datetime_iso(dt2)
    assert result2 == "2025-11-28T12:30:45.123Z"

    # Test with zero microseconds
    dt3 = datetime(2025, 11, 28, 12, 30, 45, 0, tzinfo=UTC)
    result3 = format_datetime_iso(dt3)
    assert result3 == "2025-11-28T12:30:45.000Z"


def test_format_datetime_iso_roundtrip_compatibility():
    """Test that formatted datetime can be parsed by JavaScript Date."""
    dt = datetime(2025, 11, 28, 12, 30, 45, 123456, tzinfo=UTC)
    result = format_datetime_iso(dt)

    # Should be valid ISO 8601 format parseable by JavaScript
    assert result.startswith("2025-11-28T")
    assert result.endswith("Z")
    # Should not have timezone offset (no +00:00)
    assert "+" not in result
    assert result.count(":") == 2  # HH:MM:SS only


def test_format_datetime_iso_edge_cases():
    """Test edge cases for datetime formatting."""
    # Test at midnight
    dt1 = datetime(2025, 1, 1, 0, 0, 0, 0, tzinfo=UTC)
    result1 = format_datetime_iso(dt1)
    assert result1 == "2025-01-01T00:00:00.000Z"

    # Test at end of day
    dt2 = datetime(2025, 12, 31, 23, 59, 59, 999999, tzinfo=UTC)
    result2 = format_datetime_iso(dt2)
    assert result2 == "2025-12-31T23:59:59.999Z"

    # Test leap year
    dt3 = datetime(2024, 2, 29, 12, 0, 0, 0, tzinfo=UTC)
    result3 = format_datetime_iso(dt3)
    assert result3 == "2024-02-29T12:00:00.000Z"

