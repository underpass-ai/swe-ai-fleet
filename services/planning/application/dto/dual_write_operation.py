"""DTOs for dual write ledger operations.

Following DDD:
- DTOs are simple data containers (NOT frozen if mutation needed)
- Validation in __post_init__
- No serialization methods (to_dict/from_dict forbidden)
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class DualWriteStatus(str, Enum):
    """Status of a dual write operation."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


@dataclass
class DualWriteOperation:
    """DTO representing a dual write operation in the ledger.

    Tracks the status of operations that write to both Valkey (source of truth)
    and Neo4j (projection). If Neo4j write fails, the operation remains PENDING
    until the reconciler completes it.

    Attributes:
        operation_id: Unique identifier for this operation
        status: Current status (PENDING or COMPLETED)
        attempts: Number of attempts to complete Neo4j write
        last_error: Error message from last failed attempt (if any)
        created_at: Timestamp when operation was created
        updated_at: Timestamp when operation was last updated
    """

    operation_id: str
    status: DualWriteStatus
    attempts: int
    last_error: str | None
    created_at: str  # ISO 8601 timestamp
    updated_at: str  # ISO 8601 timestamp

    def __post_init__(self) -> None:
        """Validate DTO fields.

        Raises:
            ValueError: If required fields are invalid
        """
        if not self.operation_id:
            raise ValueError("operation_id cannot be empty")

        if self.status not in (DualWriteStatus.PENDING, DualWriteStatus.COMPLETED):
            raise ValueError(f"Invalid status: {self.status}")

        if self.attempts < 0:
            raise ValueError("attempts cannot be negative")

        if not self.created_at:
            raise ValueError("created_at cannot be empty")

        if not self.updated_at:
            raise ValueError("updated_at cannot be empty")

        # Validate timestamp format
        # Handle both "Z" suffix and "+00:00" offset formats
        def normalize_timestamp(ts: str) -> str:
            """Normalize timestamp by replacing Z with +00:00 if needed."""
            if ts.endswith("Z"):
                ts_without_z = ts[:-1]
                # Check if there's already an offset (look for +HH:MM or -HH:MM pattern after T)
                # Pattern: T... followed by + or - and then digits and :
                # Check if there's already an offset pattern like +00:00 or -05:00
                offset_pattern = re.search(r"[+-]\d{2}:\d{2}$", ts_without_z)
                if offset_pattern:
                    # Already has offset, just remove Z
                    return ts_without_z
                # No offset, add +00:00
                return ts_without_z + "+00:00"
            return ts

        try:
            datetime.fromisoformat(normalize_timestamp(self.created_at))
            datetime.fromisoformat(normalize_timestamp(self.updated_at))
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid timestamp format: {self.created_at} or {self.updated_at}") from e
