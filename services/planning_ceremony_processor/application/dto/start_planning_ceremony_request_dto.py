"""DTO for starting a planning ceremony execution."""

from dataclasses import dataclass


@dataclass
class StartPlanningCeremonyRequestDTO:
    """Input DTO for starting a ceremony execution (fire-and-forget)."""

    ceremony_id: str
    definition_name: str
    story_id: str
    correlation_id: str | None
    inputs: dict[str, str]
    step_ids: tuple[str, ...]
    requested_by: str

    def __post_init__(self) -> None:
        if not self.ceremony_id or not self.ceremony_id.strip():
            raise ValueError("ceremony_id cannot be empty")
        if not self.definition_name or not self.definition_name.strip():
            raise ValueError("definition_name cannot be empty")
        if not self.story_id or not self.story_id.strip():
            raise ValueError("story_id cannot be empty")
        if self.correlation_id is not None and not self.correlation_id.strip():
            raise ValueError("correlation_id cannot be blank when provided")
        if not isinstance(self.inputs, dict):
            raise ValueError("inputs must be a dict")
        if not self.step_ids:
            raise ValueError("step_ids cannot be empty")
        if not self.requested_by or not self.requested_by.strip():
            raise ValueError("requested_by cannot be empty")
