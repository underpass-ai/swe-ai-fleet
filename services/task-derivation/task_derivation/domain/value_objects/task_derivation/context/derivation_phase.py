"""DerivationPhase value object based on enumerated phases."""

from __future__ import annotations

from enum import StrEnum


class DerivationPhase(StrEnum):
    """Enumerates supported derivation phases."""

    PLAN = "plan"
    EXECUTION = "execution"

    @classmethod
    def from_value(cls, value: str | None) -> "DerivationPhase":
        """Convert string (possibly None) into a DerivationPhase."""
        if value is None:
            return cls.PLAN

        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Invalid derivation phase: {value}") from exc

