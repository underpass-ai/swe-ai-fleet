"""Thin use case: get planning ceremony instance from processor."""

from __future__ import annotations

from dataclasses import dataclass

from planning.application.ports.planning_ceremony_processor_port import (
    PlanningCeremonyInstanceData,
    PlanningCeremonyProcessorPort,
)


@dataclass
class GetPlanningCeremonyViaProcessorUseCase:
    """Thin client use case: call Planning Ceremony Processor GetPlanningCeremonyInstance."""

    processor: PlanningCeremonyProcessorPort

    def __post_init__(self) -> None:
        if not self.processor:
            raise ValueError("processor is required (fail-fast)")

    async def execute(
        self,
        instance_id: str,
    ) -> PlanningCeremonyInstanceData | None:
        """Retrieve planning ceremony instance by ID."""
        normalized_id = (instance_id or "").strip()
        if not normalized_id:
            raise ValueError("instance_id is required")
        return await self.processor.get_planning_ceremony(normalized_id)
