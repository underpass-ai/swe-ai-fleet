"""DerivationRequestId value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DerivationRequestId:
    """Identifier returned by Ray Executor when submitting derivations."""

    value: str

    def __post_init__(self) -> None:
        """Validate identifier."""
        if not self.value or not self.value.strip():
            raise ValueError("DerivationRequestId cannot be empty")

    def __str__(self) -> str:
        """Return the raw identifier."""
        return self.value

