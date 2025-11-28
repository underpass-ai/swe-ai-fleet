"""Datetime formatting utilities for protobuf serialization.

Infrastructure layer - handles datetime formatting for external formats.
"""

from datetime import UTC, datetime


def format_datetime_iso(dt: datetime) -> str:
    """
    Format datetime to ISO 8601 string with Z suffix (UTC).

    Ensures consistent format: YYYY-MM-DDTHH:MM:SS.ssssssZ
    Converts to UTC if timezone-aware, otherwise assumes UTC.

    Args:
        dt: Datetime to format.

    Returns:
        ISO 8601 string ending with 'Z' (UTC indicator).
    """
    if dt.tzinfo is None:
        # Naive datetime - assume UTC
        dt = dt.replace(tzinfo=UTC)
    else:
        # Timezone-aware - convert to UTC
        dt = dt.astimezone(UTC)

    # Format without timezone offset, then add Z
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

