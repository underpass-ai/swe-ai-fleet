"""Use case to synchronize Story from Planning Service to Context graph."""

import logging

from core.context.domain.story import Story
from core.context.ports.graph_command_port import GraphCommandPort

logger = logging.getLogger(__name__)


class SynchronizeStoryFromPlanningUseCase:
    """Synchronize a Story from Planning Service to Context graph.

    Bounded Context: Context Service
    Trigger: planning.story.created event from Planning Service

    Following Hexagonal Architecture + DDD.
    """

    def __init__(self, graph_command: GraphCommandPort):
        """Initialize use case with dependency injection via Port."""
        self._graph = graph_command

    async def execute(self, story: Story) -> None:
        """Execute story synchronization.

        Args:
            story: Domain entity to persist
        """
        # Tell, Don't Ask: entity provides its own log context
        log_ctx = story.get_log_context()
        log_ctx["use_case"] = "SynchronizeStoryFromPlanning"

        logger.info(
            f"Synchronizing story: {story.story_id.to_string()} → epic {story.epic_id.to_string()}",
            extra=log_ctx,
        )

        # Persist via Port
        await self._graph.save_story(story)

        logger.info(
            f"✓ Story synchronized: {story.story_id.to_string()}",
            extra=log_ctx,
        )

