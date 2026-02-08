"""Thin use case: list planning ceremony instances from processor."""

from __future__ import annotations

from dataclasses import dataclass

from planning.application.ports.planning_ceremony_processor_port import (
    PlanningCeremonyInstanceData,
    PlanningCeremonyProcessorPort,
)


@dataclass
class ListPlanningCeremoniesViaProcessorUseCase:
    """Thin client use case: call Planning Ceremony Processor ListPlanningCeremonyInstances."""

    processor: PlanningCeremonyProcessorPort

    def __post_init__(self) -> None:
        if not self.processor:
            raise ValueError("processor is required (fail-fast)")

    async def execute(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        state_filter: str | None = None,
        definition_filter: str | None = None,
        story_id: str | None = None,
    ) -> tuple[list[PlanningCeremonyInstanceData], int]:
        """List planning ceremony instances with optional filtering."""
        safe_limit = limit if limit > 0 else 100
        safe_offset = offset if offset >= 0 else 0
        return await self.processor.list_planning_ceremonies(
            limit=safe_limit,
            offset=safe_offset,
            state_filter=(state_filter or "").strip() or None,
            definition_filter=(definition_filter or "").strip() or None,
            story_id=(story_id or "").strip() or None,
        )
