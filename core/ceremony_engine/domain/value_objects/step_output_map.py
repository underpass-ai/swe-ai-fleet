"""StepOutputMap: Immutable mapping of step outputs."""

from dataclasses import dataclass
from typing import Any

from core.ceremony_engine.domain.value_objects.step_id import StepId
from core.ceremony_engine.domain.value_objects.step_output_entry import StepOutputEntry


@dataclass(frozen=True)
class StepOutputMap:
    """
    Value Object: Immutable map of step_id -> output.

    Domain Invariants:
    - entries must be StepOutputEntry
    - step_id keys must be unique
    """

    entries: tuple[StepOutputEntry, ...]

    def __post_init__(self) -> None:
        seen: set[StepId] = set()
        for entry in self.entries:
            if not isinstance(entry, StepOutputEntry):
                raise ValueError(
                    f"entries must contain StepOutputEntry, got {type(entry)}"
                )
            if entry.step_id in seen:
                raise ValueError(
                    f"Duplicate step_id in StepOutputMap: {entry.step_id.value}"
                )
            seen.add(entry.step_id)

    def get(self, step_id: StepId) -> dict[str, Any] | None:
        """Get output for step_id if present."""
        for entry in self.entries:
            if entry.step_id == step_id:
                return entry.output
        return None

    def with_output(self, step_id: StepId, output: dict[str, Any]) -> "StepOutputMap":
        """Return a new StepOutputMap with updated output."""
        updated: list[StepOutputEntry] = []
        replaced = False
        for entry in self.entries:
            if entry.step_id == step_id:
                updated.append(StepOutputEntry(step_id=entry.step_id, output=output))
                replaced = True
            else:
                updated.append(entry)
        if not replaced:
            updated.append(StepOutputEntry(step_id=step_id, output=output))
        return StepOutputMap(entries=tuple(updated))
