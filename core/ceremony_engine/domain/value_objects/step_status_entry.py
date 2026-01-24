"""StepStatusEntry: Immutable entry for step status mapping."""

from dataclasses import dataclass

from core.ceremony_engine.domain.value_objects.step_id import StepId
from core.ceremony_engine.domain.value_objects.step_status import StepStatus


@dataclass(frozen=True)
class StepStatusEntry:
    """
    Value Object: Single entry for StepStatusMap.

    Domain Invariants:
    - step_id must be a non-empty string
    - status must be StepStatus
    """

    step_id: StepId
    status: StepStatus

    def __post_init__(self) -> None:
        if not isinstance(self.step_id, StepId):
            raise ValueError(f"step_id must be StepId, got {type(self.step_id)}")
        if not isinstance(self.status, StepStatus):
            raise ValueError(f"status must be StepStatus, got {type(self.status)}")
