"""Collection of observations."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.agents_and_tools.agents.domain.entities.observation_history import Observation


@dataclass
class ObservationHistories:
    """Collection of observations with utility methods."""

    observations: list[dict] = field(default_factory=list)  # List of observation dicts

    def add(self, observation: dict) -> None:
        """Add an observation to the collection."""
        self.observations.append(observation)

    def get_all(self) -> list[dict]:
        """Get all observations."""
        return self.observations

    def get_last(self) -> dict | None:
        """Get the last observation."""
        return self.observations[-1] if self.observations else None

    def get_last_n(self, n: int) -> list[dict]:
        """Get the last n observations."""
        return self.observations[-n:] if len(self.observations) >= n else self.observations

    def get_successful(self) -> list[dict]:
        """Get all successful observations."""
        return [obs for obs in self.observations if obs.get("success", False)]

    def get_failed(self) -> list[dict]:
        """Get all failed observations."""
        return [obs for obs in self.observations if not obs.get("success", True)]

    def count(self) -> int:
        """Get the number of observations."""
        return len(self.observations)

    def to_dict(self) -> list[dict]:
        """Convert to list of dicts for serialization."""
        return self.observations

