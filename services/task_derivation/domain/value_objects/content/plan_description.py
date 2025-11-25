"""PlanDescription value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanDescription:
    """Describes the implementation plan narrative."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("PlanDescription cannot be empty")

        if len(self.value) > 5000:
            raise ValueError("PlanDescription too long (max 5000 chars)")

    def __str__(self) -> str:
        return self.value

