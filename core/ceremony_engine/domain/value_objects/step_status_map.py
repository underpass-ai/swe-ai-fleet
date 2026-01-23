"""StepStatusMap: Immutable mapping of step status values."""

from dataclasses import dataclass

from core.ceremony_engine.domain.value_objects.step_id import StepId
from core.ceremony_engine.domain.value_objects.step_status import StepStatus
from core.ceremony_engine.domain.value_objects.step_status_entry import StepStatusEntry


@dataclass(frozen=True)
class StepStatusMap:
    """
    Value Object: Immutable map of step_id -> StepStatus.

    Domain Invariants:
    - step_id must be non-empty strings
    - step_id keys must be unique
    - statuses must be StepStatus
    """

    entries: tuple[StepStatusEntry, ...]

    def __post_init__(self) -> None:
        seen: set[StepId] = set()
        for entry in self.entries:
            if not isinstance(entry, StepStatusEntry):
                raise ValueError(
                    f"entries must contain StepStatusEntry, got {type(entry)}"
                )
            if entry.step_id in seen:
                raise ValueError(f"Duplicate step_id in StepStatusMap: {entry.step_id.value}")
            seen.add(entry.step_id)

    def get(self, step_id: StepId, default: StepStatus) -> StepStatus:
        """Get status for step_id or return default."""
        for entry in self.entries:
            if entry.step_id == step_id:
                return entry.status
        return default

    def with_status(self, step_id: StepId, status: StepStatus) -> "StepStatusMap":
        """Return a new StepStatusMap with updated status."""
        updated = []
        replaced = False
        for entry in self.entries:
            if entry.step_id == step_id:
                updated.append(StepStatusEntry(step_id=entry.step_id, status=status))
                replaced = True
            else:
                updated.append(entry)
        if not replaced:
            updated.append(StepStatusEntry(step_id=step_id, status=status))
        return StepStatusMap(entries=tuple(updated))
