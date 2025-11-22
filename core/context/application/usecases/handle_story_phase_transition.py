"""Use case to handle story phase transition."""

import asyncio
import logging
from typing import Any

from core.context.domain.phase_transition import PhaseTransition
from core.context.ports.graph_command_port import GraphCommandPort

logger = logging.getLogger(__name__)


class HandleStoryPhaseTransitionUseCase:
    """Handle story phase transition (cache invalidation + audit trail).

    Bounded Context: Context Service
    Trigger: planning.story.transitioned event from Planning Service

    Responsibility:
    - Invalidate context cache for the story (contexts depend on phase)
    - Record phase transition in graph for audit trail

    Following Hexagonal Architecture + DDD.
    Note: Cache is optional (may be None in some deployments).
    """

    def __init__(self, graph_command: GraphCommandPort, cache_service: Any | None = None):
        """Initialize use case with dependency injection via Ports.

        Args:
            graph_command: Port for graph persistence
            cache_service: Optional cache service (Valkey/Redis client)
        """
        self._graph = graph_command
        self._cache = cache_service

    async def execute(self, transition: PhaseTransition) -> None:
        """Execute phase transition handling.

        Args:
            transition: PhaseTransition domain entity
        """
        # Tell, Don't Ask: entity provides its own log context
        log_ctx = transition.get_log_context()
        log_ctx["use_case"] = "HandleStoryPhaseTransition"

        logger.info(
            f"Handling story phase transition: {transition.story_id.to_string()} "
            f"{transition.from_phase} → {transition.to_phase}",
            extra=log_ctx,
        )

        # 1. Invalidate context cache (if cache exists)
        if self._cache:
            deleted_count = await self._invalidate_cache(
                transition.story_id.to_string(),
            )
            logger.info(
                f"Invalidated {deleted_count} cache entries for {transition.story_id.to_string()} "
                f"(phase: {transition.to_phase})"
            )

        # 2. Record phase transition in graph (audit trail)
        await self._graph.save_phase_transition(transition)

        logger.info(
            f"✓ Phase transition handled: {transition.story_id.to_string()} "
            f"{transition.from_phase}→{transition.to_phase}",
            extra=log_ctx,
        )

    async def _invalidate_cache(self, story_id: str) -> int:
        """Invalidate all context cache entries for a story.

        When a story transitions phases, all pre-computed contexts become invalid
        and must be regenerated with the new phase constraints.

        Args:
            story_id: Story ID to invalidate cache for

        Returns:
            Number of cache entries deleted
        """
        try:
            pattern = f"context:{story_id}:*"
            cursor = 0
            deleted_count = 0
            max_iterations = 1000  # Safety limit
            iteration = 0

            while iteration < max_iterations:
                cursor, keys = await asyncio.to_thread(
                    self._cache.scan,
                    cursor=cursor,
                    match=pattern,
                    count=100,
                )
                if keys:
                    deleted = await asyncio.to_thread(
                        self._cache.delete,
                        *keys,
                    )
                    deleted_count += deleted

                # Yield control to event loop (prevent blocking)
                await asyncio.sleep(0)

                # Redis SCAN cursor returns to 0 when complete
                if cursor == 0:
                    break

                iteration += 1

            if iteration >= max_iterations:
                logger.warning(
                    f"Cache invalidation for {story_id} reached max iterations "
                    f"({max_iterations}), may be incomplete"
                )

            return deleted_count

        except Exception as e:
            logger.warning(f"Failed to invalidate cache for {story_id}: {e}")
            return 0  # Don't fail the whole operation if cache fails

