"""TaskConstraints value object for backlog review.

Represents constraints and requirements for task execution during backlog review.
This is a domain value object, not tied to any port or adapter.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BacklogReviewTaskConstraints:
    """
    Constraints and requirements for backlog review task execution.

    Domain Value Object:
    - Encapsulates role-specific constraints for backlog review
    - Used by BacklogReviewDeliberationRequest entity
    - Converted to port DTOs by infrastructure mappers

    Domain Invariants:
    - rubric cannot be empty
    - requirements is a tuple of strings (can be empty)
    - timeout_seconds must be > 0
    - max_iterations must be > 0
    """

    rubric: str
    requirements: tuple[str, ...]
    timeout_seconds: int = 180
    max_iterations: int = 3
    metadata: dict[str, str] | None = None

    def __post_init__(self) -> None:
        """Validate constraints (fail-fast).

        Raises:
            ValueError: If any parameter is invalid
        """
        if not self.rubric or not self.rubric.strip():
            raise ValueError("rubric cannot be empty")

        if self.timeout_seconds <= 0:
            raise ValueError(
                f"timeout_seconds must be > 0, got {self.timeout_seconds}"
            )

        if self.max_iterations <= 0:
            raise ValueError(
                f"max_iterations must be > 0, got {self.max_iterations}"
            )

