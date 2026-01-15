"""Output: Value Object representing a single output specification."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Output:
    """
    Value Object: Output specification.

    Domain Invariants:
    - type must be one of: "object", "array", "string", "number", "boolean"
    - schema is optional (dict describing the output structure)
    - Immutable (frozen=True)

    Business Rules:
    - Defines the structure of a ceremony output
    - schema is recommended for complex outputs (object/array types)
    - Schema validation happens at infrastructure layer
    """

    type: str  # "object", "array", "string", "number", "boolean"
    schema: dict[str, Any] | None = None

    VALID_TYPES = {"object", "array", "string", "number", "boolean"}

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Raises:
            ValueError: If output is invalid
        """
        if not self.type or not self.type.strip():
            raise ValueError("Output type cannot be empty")

        if self.type not in self.VALID_TYPES:
            raise ValueError(
                f"Output type must be one of {', '.join(sorted(self.VALID_TYPES))}: {self.type}"
            )
