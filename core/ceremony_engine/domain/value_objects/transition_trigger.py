"""TransitionTrigger: Value Object representing a transition trigger."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TransitionTrigger:
    """
    Value Object: Transition trigger identifier.

    Domain Invariants:
    - value must be non-empty
    - value must be a string
    """

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("TransitionTrigger value cannot be empty")
