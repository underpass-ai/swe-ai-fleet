"""Response DTO for deliberation status."""

from dataclasses import dataclass

from services.ray_executor.domain.entities import (
    DeliberationResult,
    MultiAgentDeliberationResult,
)


@dataclass(frozen=True)
class DeliberationStatusResponse:
    """Response with deliberation status.

    Attributes:
        status: Current status ("running", "completed", "failed", "not_found")
        result: Deliberation result (single or multi-agent) if completed, None otherwise
        error_message: Error message if failed, None otherwise
    """

    status: str
    result: DeliberationResult | MultiAgentDeliberationResult | None = None
    error_message: str | None = None

