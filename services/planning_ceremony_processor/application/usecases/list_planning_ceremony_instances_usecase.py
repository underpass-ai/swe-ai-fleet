"""Use case for listing planning ceremony instances."""

from dataclasses import dataclass

from core.ceremony_engine.application.ports.persistence_port import PersistencePort
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance


@dataclass
class ListPlanningCeremonyInstancesUseCase:
    """List planning ceremony instances with optional filtering."""

    persistence_port: PersistencePort

    def __post_init__(self) -> None:
        if not self.persistence_port:
            raise ValueError("persistence_port is required (fail-fast)")

    async def execute(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        state_filter: str | None = None,
        definition_filter: str | None = None,
        story_id: str | None = None,
    ) -> tuple[list[CeremonyInstance], int]:
        """List instances with pagination and optional filters."""
        safe_limit = limit if limit > 0 else 100
        safe_offset = offset if offset >= 0 else 0
        return await self.persistence_port.list_instances(
            limit=safe_limit,
            offset=safe_offset,
            state_filter=(state_filter or "").strip() or None,
            definition_filter=(definition_filter or "").strip() or None,
            story_id=(story_id or "").strip() or None,
        )
