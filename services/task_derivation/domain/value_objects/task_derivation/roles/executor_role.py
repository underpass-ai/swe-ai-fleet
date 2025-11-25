"""ExecutorRole value object used when submitting derivations to Ray."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutorRole:
    """Immutable representation of the role executed by Ray workers."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("ExecutorRole cannot be empty")

    def __str__(self) -> str:
        return self.value

