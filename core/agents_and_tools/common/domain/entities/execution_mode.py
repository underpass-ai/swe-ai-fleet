"""Execution mode value object."""

from dataclasses import dataclass
from enum import Enum


class ExecutionModeEnum(str, Enum):
    """Enumeration of agent execution modes.

    Modes:
    - FULL: Agent can use all tools including write operations
    - READ_ONLY: Agent can only use read operations (analysis/planning mode)
    """

    FULL = "full"
    READ_ONLY = "read_only"


@dataclass(frozen=True)
class ExecutionMode:
    """Value Object: Agent execution mode.

    Determines whether agent can perform write operations or only read.

    Domain Invariants:
    - Mode must be valid ExecutionModeEnum
    - Mode is immutable

    Examples:
        >>> mode = ExecutionMode(value=ExecutionModeEnum.FULL)
        >>> mode.is_full()
        True
        >>> mode.allows_write()
        True
    """

    value: ExecutionModeEnum

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Type checking is handled by type hints.
        No additional business rules to validate.
        """
        pass  # No validation needed, type hint ensures ExecutionModeEnum

    def is_full(self) -> bool:
        """Check if mode is full execution."""
        return self.value == ExecutionModeEnum.FULL

    def is_read_only(self) -> bool:
        """Check if mode is read-only."""
        return self.value == ExecutionModeEnum.READ_ONLY

    def allows_write(self) -> bool:
        """Check if mode allows write operations.

        Tell, Don't Ask: Mode knows if writes are allowed.
        """
        return self.value == ExecutionModeEnum.FULL

    def __str__(self) -> str:
        """String representation."""
        return self.value.value

