"""Use case for retrieving a planning ceremony instance by ID."""

from dataclasses import dataclass

from core.ceremony_engine.application.ports.persistence_port import PersistencePort
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance


@dataclass
class GetPlanningCeremonyInstanceUseCase:
    """Retrieve a single planning ceremony instance from persistence."""

    persistence_port: PersistencePort

    def __post_init__(self) -> None:
        if not self.persistence_port:
            raise ValueError("persistence_port is required (fail-fast)")

    async def execute(self, instance_id: str) -> CeremonyInstance | None:
        """Retrieve instance by ID."""
        normalized_id = (instance_id or "").strip()
        if not normalized_id:
            raise ValueError("instance_id cannot be empty")
        return await self.persistence_port.load_instance(normalized_id)
