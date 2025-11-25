"""TechnicalNotes value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TechnicalNotes:
    """Captures technical considerations for a plan."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("TechnicalNotes cannot be empty")

    def __str__(self) -> str:
        return self.value

