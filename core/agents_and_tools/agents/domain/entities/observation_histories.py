"""Collection of observations."""

from dataclasses import dataclass, field
from typing import Any

from core.agents_and_tools.agents.domain.entities.execution_step import ExecutionStep
from core.agents_and_tools.agents.domain.entities.observation_history import Observation


@dataclass
class ObservationHistories:
    """Collection of observations with utility methods."""

    observations: list[Observation] = field(default_factory=list)  # List of Observation entities

    def add(
        self,
        iteration: int,
        action: ExecutionStep,
        result: Any,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Add an observation to the collection."""
        obs_entity = Observation(
            iteration=iteration,
            action=action,
            result=result,
            success=success,
            error=error,
        )
        self.observations.append(obs_entity)

    def get_all(self) -> list[Observation]:
        """Get all observations."""
        return self.observations

    def get_last(self) -> Observation | None:
        """Get the last observation."""
        return self.observations[-1] if self.observations else None

    def get_last_n(self, n: int) -> list[Observation]:
        """Get the last n observations."""
        return self.observations[-n:] if len(self.observations) >= n else self.observations

    def get_successful(self) -> list[Observation]:
        """Get all successful observations."""
        return [obs for obs in self.observations if obs.success]

    def get_failed(self) -> list[Observation]:
        """Get all failed observations."""
        return [obs for obs in self.observations if not obs.success]

    def count(self) -> int:
        """Get the number of observations."""
        return len(self.observations)

