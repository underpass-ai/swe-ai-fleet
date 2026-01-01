"""Idempotency state enumeration.

Defines the states for idempotency tracking:
- PENDING: Request received, not yet processed
- IN_PROGRESS: Request is currently being processed
- COMPLETED: Request completed successfully
"""

from enum import Enum


class IdempotencyState(str, Enum):
    """Idempotency processing states.

    State transitions:
    - PENDING → IN_PROGRESS (when handler starts)
    - IN_PROGRESS → COMPLETED (when handler succeeds)
    - IN_PROGRESS → PENDING (if stale detected, allow retry)

    States are used to:
    - Prevent duplicate processing (COMPLETED)
    - Detect concurrent processing (IN_PROGRESS)
    - Handle stale locks (IN_PROGRESS with expired TTL)
    """

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

    def is_terminal(self) -> bool:
        """Check if this is a terminal state (no further processing needed).

        Returns:
            True if COMPLETED (terminal), False otherwise
        """
        return self == IdempotencyState.COMPLETED

    def is_in_progress(self) -> bool:
        """Check if request is currently being processed.

        Returns:
            True if IN_PROGRESS, False otherwise
        """
        return self == IdempotencyState.IN_PROGRESS
