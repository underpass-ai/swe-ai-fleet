"""Domain entity for audit trail entry."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class AuditTrailEntry:
    """Single audit trail entry."""

    timestamp: datetime  # When the event occurred
    event_type: str  # Type of event (operation_start, operation_end, error, etc.)
    details: dict[str, Any]  # Event details
    success: bool = True  # Whether the event was successful
    error: str | None = None  # Error message if failed

