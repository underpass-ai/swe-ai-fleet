"""DTO for execution plan from LLM."""

from dataclasses import dataclass

from core.agents_and_tools.agents.domain.entities import ExecutionStep


@dataclass(frozen=True)
class PlanDTO:
    """
    DTO for execution plan returned by GeneratePlanUseCase.

    This DTO represents the structure returned by the LLM when generating
    execution plans. Following cursorrules, this is a simple DTO with
    no serialization methods.
    """

    steps: list[ExecutionStep]
    reasoning: str

    def __post_init__(self) -> None:
        """Validate DTO invariants."""
        if not self.reasoning:
            raise ValueError("reasoning cannot be empty")

