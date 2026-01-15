"""Inputs: Value Object representing required and optional inputs."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Inputs:
    """
    Value Object: Ceremony inputs specification.

    Domain Invariants:
    - required is a tuple of input field names (non-empty strings)
    - optional is a tuple of input field names (non-empty strings)
    - Input names must be valid identifiers (snake_case)
    - Immutable (frozen=True)

    Business Rules:
    - Defines what inputs a ceremony requires
    - required inputs must be provided when starting a ceremony
    - optional inputs may be provided but are not mandatory
    - Input names should follow snake_case convention
    """

    required: tuple[str, ...]
    optional: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Raises:
            ValueError: If inputs are invalid
        """
        # Validate required inputs
        for input_name in self.required:
            if not input_name or not input_name.strip():
                raise ValueError("Required input name cannot be empty")

            # Validate snake_case (simple check: lowercase with underscores, no spaces)
            if not input_name.replace("_", "").isalnum():
                raise ValueError(f"Required input name must be valid identifier (snake_case): {input_name}")

        # Validate optional inputs
        for input_name in self.optional:
            if not input_name or not input_name.strip():
                raise ValueError("Optional input name cannot be empty")

            # Validate snake_case
            if not input_name.replace("_", "").isalnum():
                raise ValueError(f"Optional input name must be valid identifier (snake_case): {input_name}")

        # Check for duplicates between required and optional
        required_set = set(self.required)
        optional_set = set(self.optional)
        duplicates = required_set & optional_set
        if duplicates:
            raise ValueError(
                f"Input names cannot be both required and optional: {', '.join(sorted(duplicates))}"
            )
