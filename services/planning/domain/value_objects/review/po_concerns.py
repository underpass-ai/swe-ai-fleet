"""PoConcerns - Value Object for PO concerns or risks to monitor.

Domain Layer (Value Object):
- Encapsulates PO's concerns or risks identified during approval
- Optional field for monitoring and risk management
- Immutable text content with validation
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PoConcerns:
    """
    Value object representing PO's concerns or risks to monitor.

    This is an optional field that allows the PO to document any concerns,
    risks, or items that need to be monitored during implementation.

    Following DDD:
    - Immutable value object (@dataclass(frozen=True))
    - Rich validation in __post_init__
    - Business rules enforced at construction
    - Self-documenting domain concept

    Domain Invariants:
    - If provided, concerns cannot be empty or whitespace-only
    - Concerns must contain meaningful content (not just spaces)
    """

    value: str

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Validation rules:
        1. If provided, concerns cannot be empty
        2. Concerns cannot be whitespace-only

        Raises:
            ValueError: If validation fails
        """
        if not self.value or not self.value.strip():
            raise ValueError(
                "PoConcerns cannot be empty: If provided, concerns must contain "
                "meaningful content (not just whitespace)"
            )

    def __str__(self) -> str:
        """String representation.

        Returns:
            The concerns value
        """
        return self.value

    def __repr__(self) -> str:
        """Developer representation.

        Returns:
            Developer-friendly string representation
        """
        return f"PoConcerns(value='{self.value[:50]}...' if len(self.value) > 50 else self.value)"

