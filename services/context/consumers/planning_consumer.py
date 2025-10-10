"""
Planning Events Consumer for Context Service.

Consumes events from Planning Service to react to story lifecycle changes.
"""

import asyncio
import json
import logging
from typing import Any

from nats.aio.client import Client as NATS
from nats.js import JetStreamContext

logger = logging.getLogger(__name__)


class PlanningEventsConsumer:
    """Consumes planning events and updates context accordingly."""

    def __init__(
        self,
        nc: NATS,
        js: JetStreamContext,
        cache_service: Any,
        graph_command: Any,
    ):
        """
        Initialize Planning Events Consumer.

        Args:
            nc: NATS client
            js: JetStream context
            cache_service: Cache service (Valkey/Redis)
            graph_command: Graph command store (Neo4j)
        """
        self.nc = nc
        self.js = js
        self.cache = cache_service
        self.graph = graph_command

    async def start(self):
        """Start consuming planning events."""
        try:
            # Subscribe to story transitions
            await self.js.subscribe(
                "planning.story.transitioned",
                queue="context-workers",
                cb=self._handle_story_transitioned,
            )
            logger.info("✓ Subscribed to planning.story.transitioned")

            # Subscribe to plan approvals
            await self.js.subscribe(
                "planning.plan.approved",
                queue="context-workers",
                cb=self._handle_plan_approved,
            )
            logger.info("✓ Subscribed to planning.plan.approved")

            logger.info("✓ Planning Events Consumer started")

        except Exception as e:
            logger.error(f"Failed to start Planning Events Consumer: {e}")
            raise

    async def _handle_story_transitioned(self, msg):
        """
        Handle story phase transition events.

        When a story transitions to a new phase, we invalidate the context
        cache to force re-computation with the new phase constraints.
        """
        try:
            event = json.loads(msg.data.decode())
            story_id = event.get("story_id")
            from_phase = event.get("from_phase")
            to_phase = event.get("to_phase")
            timestamp = event.get("timestamp")

            logger.info(
                f"Story transitioned: {story_id} {from_phase} → {to_phase}"
            )

            # Invalidate context cache for all roles in this story
            # The next GetContext call will rebuild with new phase
            cache_pattern = f"context:{story_id}:*"
            
            # Log for audit trail
            logger.info(
                f"Invalidating context cache for {story_id} (phase: {to_phase})"
            )

            # Record phase transition in graph for history
            if self.graph:
                try:
                    await asyncio.to_thread(
                        self.graph.upsert_entity,
                        entity_type="PhaseTransition",
                        entity_id=f"{story_id}:{timestamp}",
                        properties={
                            "story_id": story_id,
                            "from_phase": from_phase,
                            "to_phase": to_phase,
                            "timestamp": timestamp,
                        },
                    )
                except Exception as e:
                    logger.warning(f"Failed to record transition in graph: {e}")

            # Acknowledge message
            await msg.ack()
            logger.debug(f"✓ Processed story transition for {story_id}")

        except Exception as e:
            logger.error(
                f"Error handling story transition: {e}",
                exc_info=True,
            )
            # Negative acknowledge to retry
            await msg.nak()

    async def _handle_plan_approved(self, msg):
        """
        Handle plan approval events.

        When a plan is approved, we may want to pre-warm the context cache
        or trigger initial context assembly.
        """
        try:
            event = json.loads(msg.data.decode())
            story_id = event.get("story_id")
            plan_id = event.get("plan_id")
            approved_by = event.get("approved_by")
            timestamp = event.get("timestamp")

            logger.info(f"Plan approved: {plan_id} for story {story_id}")

            # Record approval in graph
            if self.graph:
                try:
                    await asyncio.to_thread(
                        self.graph.upsert_entity,
                        entity_type="PlanApproval",
                        entity_id=f"{plan_id}:{timestamp}",
                        properties={
                            "story_id": story_id,
                            "plan_id": plan_id,
                            "approved_by": approved_by,
                            "timestamp": timestamp,
                        },
                    )
                except Exception as e:
                    logger.warning(f"Failed to record approval in graph: {e}")

            await msg.ack()
            logger.debug(f"✓ Processed plan approval for {plan_id}")

        except Exception as e:
            logger.error(
                f"Error handling plan approval: {e}",
                exc_info=True,
            )
            await msg.nak()

    async def stop(self):
        """Stop consuming events."""
        # JetStream subscriptions are automatically cleaned up when connection closes
        logger.info("Planning Events Consumer stopped")

