"""Step: Value Object representing an executable step."""

from dataclasses import dataclass
from typing import Any

from core.ceremony_engine.domain.value_objects.retry_policy import RetryPolicy
from core.ceremony_engine.domain.value_objects.step_handler_type import StepHandlerType


@dataclass(frozen=True)
class Step:
    """
    Value Object: Executable step.

    Domain Invariants:
    - id must be non-empty, snake_case (e.g., "score_stories")
    - state must be non-empty (references a State id, validated at CeremonyDefinition level)
    - handler must be a valid StepHandlerType
    - config must be a non-empty dict (handler-specific configuration)
    - retry is optional (RetryPolicy if provided)
    - timeout_seconds is optional (must be > 0 if provided)
    - Immutable (frozen=True)

    Business Rules:
    - Steps define executable operations within states
    - Handler type determines what kind of operation the step performs
    - Config structure varies by handler type (validated at infrastructure layer)
    - State must reference an existing state (validated at CeremonyDefinition level)
    """

    id: str  # snake_case identifier
    state: str  # State ID
    handler: StepHandlerType
    config: dict[str, Any]
    retry: RetryPolicy | None = None
    timeout_seconds: int | None = None

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Raises:
            ValueError: If step is invalid
        """
        if not self.id or not self.id.strip():
            raise ValueError("Step id cannot be empty")

        # Validate snake_case (simple check: lowercase with underscores, no spaces)
        if " " in self.id:
            raise ValueError(f"Step id must be snake_case (no spaces): {self.id}")
        if not self.id.replace("_", "").isalnum() or not self.id.replace("_", "").islower():
            raise ValueError(f"Step id must be snake_case: {self.id}")

        if not self.state or not self.state.strip():
            raise ValueError("Step state cannot be empty")

        if not isinstance(self.config, dict):
            raise ValueError("Step config must be a dict")

        if not self.config:
            raise ValueError("Step config cannot be empty")

        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError(
                f"Step timeout_seconds must be > 0 if provided: {self.timeout_seconds}"
            )

    def __str__(self) -> str:
        """String representation for logging."""
        return f"{self.id} ({self.handler.value})"
