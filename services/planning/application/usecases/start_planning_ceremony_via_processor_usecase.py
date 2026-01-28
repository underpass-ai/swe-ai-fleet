"""Thin use case: forward StartPlanningCeremony to Planning Ceremony Processor (fire-and-forget)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from planning.application.ports.planning_ceremony_processor_port import (
    PlanningCeremonyProcessorPort,
)

logger = logging.getLogger(__name__)


@dataclass
class StartPlanningCeremonyViaProcessorUseCase:
    """Thin client use case: call Planning Ceremony Processor StartPlanningCeremony."""

    processor: PlanningCeremonyProcessorPort

    def __post_init__(self) -> None:
        if not self.processor:
            raise ValueError("processor is required (fail-fast)")

    async def execute(
        self,
        ceremony_id: str,
        definition_name: str,
        story_id: str,
        step_ids: tuple[str, ...],
        requested_by: str,
        correlation_id: str | None = None,
        inputs: dict[str, str] | None = None,
    ) -> str:
        """Start planning ceremony via processor (fire-and-forget).

        Returns instance_id. Raises PlanningCeremonyProcessorError on gRPC failure.
        """
        return await self.processor.start_planning_ceremony(
            ceremony_id=ceremony_id,
            definition_name=definition_name,
            story_id=story_id,
            step_ids=step_ids,
            requested_by=requested_by,
            correlation_id=correlation_id,
            inputs=inputs,
        )
