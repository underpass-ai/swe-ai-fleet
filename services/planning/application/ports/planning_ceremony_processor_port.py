"""Port for Planning Ceremony Processor (thin client).

Planning Service calls Planning Ceremony Processor gRPC to start ceremony
executions (fire-and-forget). Following Hexagonal Architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class PlanningCeremonyProcessorError(Exception):
    """Raised when Planning Ceremony Processor gRPC fails."""

    pass


class PlanningCeremonyProcessorPort(ABC):
    """Port for Planning Ceremony Processor (thin client).

    Fire-and-forget: start_planning_ceremony returns immediately with instance_id.
    Ceremony execution runs asynchronously in the processor.
    """

    @abstractmethod
    async def start_planning_ceremony(
        self,
        ceremony_id: str,
        definition_name: str,
        story_id: str,
        step_ids: tuple[str, ...],
        requested_by: str,
        correlation_id: str | None = None,
        inputs: dict[str, str] | None = None,
    ) -> str:
        """Start a planning ceremony (fire-and-forget).

        Args:
            ceremony_id: Ceremony identifier.
            definition_name: YAML definition name (e.g. dummy_ceremony).
            story_id: Story identifier.
            step_ids: Step IDs to execute immediately.
            requested_by: User or system initiating.
            correlation_id: Optional correlation ID for tracing.
            inputs: Optional inputs for ceremony execution.

        Returns:
            Instance ID (e.g. "{ceremony_id}:{story_id}").

        Raises:
            PlanningCeremonyProcessorError: If gRPC call fails.
        """
        pass
