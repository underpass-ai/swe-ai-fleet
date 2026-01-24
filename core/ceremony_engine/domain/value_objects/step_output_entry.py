"""StepOutputEntry: Value object representing step output."""

from dataclasses import dataclass
from typing import Any

from core.ceremony_engine.domain.value_objects.step_id import StepId


@dataclass(frozen=True)
class StepOutputEntry:
    """
    Value Object: Step output entry.

    Domain Invariants:
    - step_id must be StepId
    - output must be a dict
    """

    step_id: StepId
    output: dict[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.step_id, StepId):
            raise ValueError(f"step_id must be StepId, got {type(self.step_id)}")
        if not isinstance(self.output, dict):
            raise ValueError(f"output must be a dict, got {type(self.output)}")
