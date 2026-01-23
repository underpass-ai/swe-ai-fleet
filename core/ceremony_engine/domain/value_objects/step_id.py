"""StepId: Value Object representing a step identifier."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StepId:
    """
    Value Object: Step identifier.

    Domain Invariants:
    - value must be non-empty, snake_case
    """

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("StepId value cannot be empty")
        if " " in self.value:
            raise ValueError(f"StepId must be snake_case (no spaces): {self.value}")
        if not self.value.replace("_", "").isalnum() or not self.value.replace("_", "").islower():
            raise ValueError(f"StepId must be snake_case: {self.value}")
