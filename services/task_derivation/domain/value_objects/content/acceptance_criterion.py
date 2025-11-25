"""AcceptanceCriterion value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AcceptanceCriterion:
    """Single acceptance criterion statement."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("AcceptanceCriterion cannot be empty")

    def __str__(self) -> str:
        return self.value

