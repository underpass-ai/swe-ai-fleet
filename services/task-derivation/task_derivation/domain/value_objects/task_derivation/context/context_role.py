"""ContextRole value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextRole:
    """Immutable role identifier for context retrieval."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("ContextRole cannot be empty")

    def __str__(self) -> str:
        return self.value

