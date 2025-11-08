"""ActorId value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ActorId:
    """Value Object for Actor identifier."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("ActorId cannot be empty")

    def to_string(self) -> str:
        """Convert to string representation.

        Explicit method following Tell, Don't Ask principle.
        """
        return self.value

    def __str__(self) -> str:
        """String representation for compatibility."""
        return self.to_string()






