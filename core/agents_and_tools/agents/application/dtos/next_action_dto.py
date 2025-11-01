"""DTO for next action decision from LLM."""

from dataclasses import dataclass

from core.agents_and_tools.agents.domain.entities import ExecutionStep


@dataclass(frozen=True)
class NextActionDTO:
    """
    DTO for next action decision returned by GenerateNextActionUseCase.

    This DTO represents the structure returned by the LLM when deciding
    the next action in ReAct-style execution. Following cursorrules,
    this is a simple DTO with no serialization methods.
    """

    done: bool
    step: ExecutionStep | None
    reasoning: str

    def __post_init__(self) -> None:
        """Validate DTO invariants."""
        if not self.reasoning:
            raise ValueError("reasoning cannot be empty")
        if not self.done and self.step is None:
            raise ValueError("step cannot be None when done=False")

