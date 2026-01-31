"""Use case to record milestone/event in graph."""

import asyncio
import logging

from core.context.ports.graph_command_port import GraphCommandPort

logger = logging.getLogger(__name__)


class RecordMilestoneUseCase:
    """Record a milestone/event in the graph.

    Bounded Context: Context Service

    Responsibility:
    - Record significant events/milestones
    - Create audit trail in Neo4j

    Following Hexagonal Architecture + DDD.
    """

    def __init__(self, graph_command: GraphCommandPort):
        """Initialize use case with dependency injection via Port."""
        self._graph = graph_command

    async def execute(
        self,
        milestone_id: str,
        story_id: str,
        event_type: str,
        description: str,
        timestamp_ms: int,
    ) -> None:
        """Execute milestone recording.

        Args:
            milestone_id: Unique milestone identifier
            story_id: Parent story ID
            event_type: Type of event/milestone
            description: Event description
            timestamp_ms: Event timestamp
        """
        logger.info(
            f"Recording milestone: {milestone_id} for story {story_id}",
            extra={
                "milestone_id": milestone_id,
                "story_id": story_id,
                "event_type": event_type,
                "use_case": "RecordMilestone",
            },
        )

        # Persist via Port (adapter is sync; run in thread to avoid blocking)
        properties = {
            "id": milestone_id,
            "case_id": story_id,
            "event_type": event_type,
            "description": description,
            "timestamp_ms": timestamp_ms,
        }
        await asyncio.to_thread(
            self._graph.upsert_entity,
            "Event",
            milestone_id,
            properties,
        )

        logger.info(
            f"✓ Milestone recorded: {milestone_id}",
            extra={"milestone_id": milestone_id},
        )

