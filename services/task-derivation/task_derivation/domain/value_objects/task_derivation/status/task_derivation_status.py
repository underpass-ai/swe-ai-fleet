"""TaskDerivationStatus value object."""

from __future__ import annotations

from enum import StrEnum


class TaskDerivationStatus(StrEnum):
    """Enumeration of possible derivation outcomes."""

    SUCCESS = "success"
    FAILED = "failed"

    @classmethod
    def from_value(cls, value: str) -> TaskDerivationStatus:
        """Parse status from primitive string (fail-fast)."""
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Invalid derivation status: {value}") from exc

    def is_success(self) -> bool:
        """Check if status represents success."""
        return self is TaskDerivationStatus.SUCCESS

    def is_failure(self) -> bool:
        """Check if status represents failure."""
        return self is TaskDerivationStatus.FAILED

