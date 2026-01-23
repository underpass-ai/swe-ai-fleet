"""GuardName: Value Object representing a guard identifier."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardName:
    """
    Value Object: Guard identifier.

    Domain Invariants:
    - value must be non-empty
    - value must be a string
    """

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("GuardName value cannot be empty")
