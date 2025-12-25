"""PoNotes - Value Object for PO approval notes.

Domain Layer (Value Object):
- Encapsulates PO's explanation of WHY they approve a plan
- Required for semantic traceability and accountability
- Immutable text content with validation
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PoNotes:
    """
    Value object representing PO's explanation of why they approve a plan.

    This is a required field for all approvals to ensure semantic traceability.
    The PO must explain their decision rationale for future reference and
    accountability.

    Following DDD:
    - Immutable value object (@dataclass(frozen=True))
    - Rich validation in __post_init__
    - Business rules enforced at construction
    - Self-documenting domain concept

    Domain Invariants:
    - Notes cannot be empty or whitespace-only
    - Notes must contain meaningful content (not just spaces)
    """

    value: str

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Validation rules:
        1. Notes cannot be empty
        2. Notes cannot be whitespace-only

        Raises:
            ValueError: If validation fails
        """
        if not self.value or not self.value.strip():
            raise ValueError(
                "PoNotes cannot be empty: PO must explain WHY they approve the plan "
                "(required for semantic traceability and accountability)"
            )

    def __str__(self) -> str:
        """String representation.

        Returns:
            The notes value
        """
        return self.value

    def __repr__(self) -> str:
        """Developer representation.

        Returns:
            Developer-friendly string representation
        """
        return f"PoNotes(value='{self.value[:50]}...' if len(self.value) > 50 else self.value)"

