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
            cache_service: Cache service (Valkey/Redis) - redis.Redis client
            graph_command: Graph command store (Neo4j)
        """
        self.nc = nc
        self.js = js
        self.cache = cache_service  # This is the redis.Redis client
        self.graph = graph_command

    async def start(self):
        """Start consuming planning events with DURABLE PULL consumers."""
        try:
            # Create PULL subscriptions instead of PUSH
            # This allows multiple pods to share the same durable consumer
            
            # Pull consumer for story transitions
            self._story_sub = await self.js.pull_subscribe(
                subject="planning.story.transitioned",
                durable="context-planning-story-transitions",
                stream="PLANNING_EVENTS",
            )
            logger.info("✓ Pull subscription created for planning.story.transitioned (DURABLE)")

            # Pull consumer for plan approvals
            self._plan_sub = await self.js.pull_subscribe(
                subject="planning.plan.approved",
                durable="context-planning-plan-approved",
                stream="PLANNING_EVENTS",
            )
            logger.info("✓ Pull subscription created for planning.plan.approved (DURABLE)")

            # Start background tasks to fetch and process messages
            import asyncio
            self._tasks = [
                asyncio.create_task(self._poll_story_transitions()),
                asyncio.create_task(self._poll_plan_approvals()),
            ]

            logger.info("✓ Planning Events Consumer started with DURABLE PULL consumers")

        except Exception as e:
            logger.error(f"Failed to start Planning Events Consumer: {e}", exc_info=True)
            raise
    
    async def _poll_story_transitions(self):
        """Poll for story transition messages."""
        logger.info("🔄 Background task _poll_story_transitions started")
        while True:
            try:
                logger.info("📥 Fetching story transitions (timeout=5s)...")
                msgs = await self._story_sub.fetch(batch=1, timeout=5)
                logger.info(f"✅ Received {len(msgs)} story transition messages")
                for msg in msgs:
                    await self._handle_story_transitioned(msg)
            except TimeoutError:
                # No messages, continue polling
                logger.info("⏱️  No story transitions (timeout), continuing...")
                continue
            except Exception as e:
                logger.error(f"❌ Error polling story transitions: {e}", exc_info=True)
                await asyncio.sleep(5)
    
    async def _poll_plan_approvals(self):
        """Poll for plan approval messages."""
        logger.info("🔄 Background task _poll_plan_approvals started")
        while True:
            try:
                logger.info("📥 Fetching plan approvals (timeout=5s)...")
                msgs = await self._plan_sub.fetch(batch=1, timeout=5)
                logger.info(f"✅ Received {len(msgs)} plan approval messages")
                for msg in msgs:
                    await self._handle_plan_approved(msg)
            except TimeoutError:
                # No messages, continue polling
                logger.info("⏱️  No plan approvals (timeout), continuing...")
                continue
            except Exception as e:
                logger.error(f"❌ Error polling plan approvals: {e}", exc_info=True)
                await asyncio.sleep(5)

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
            if self.cache:
                try:
                    # Delete all context keys for this story
                    pattern = f"context:{story_id}:*"
                    
                    # Scan for keys matching pattern (more efficient than KEYS)
                    cursor = 0
                    deleted_count = 0
                    while True:
                        cursor, keys = await asyncio.to_thread(
                            self.cache.scan,
                            cursor=cursor,
                            match=pattern,
                            count=100
                        )
                        if keys:
                            deleted = await asyncio.to_thread(
                                self.cache.delete,
                                *keys
                            )
                            deleted_count += deleted
                        if cursor == 0:
                            break
                    
                    logger.info(
                        f"Invalidated {deleted_count} context cache entries for {story_id} "
                        f"(phase: {to_phase})"
                    )
                except Exception as e:
                    logger.warning(f"Failed to invalidate cache: {e}")

            # Record phase transition in graph for history
            if self.graph:
                try:
                    await asyncio.to_thread(
                        self.graph.upsert_entity,
                        label="PhaseTransition",  # ← CORRECTED: parameter name
                        id=f"{story_id}:{timestamp}",  # ← CORRECTED: parameter name
                        properties={
                            "story_id": story_id,
                            "from_phase": from_phase,
                            "to_phase": to_phase,
                            "timestamp": timestamp,
                        },
                    )
                    logger.info(f"✓ PhaseTransition recorded in Neo4j: {story_id} {from_phase}→{to_phase}")
                except Exception as e:
                    logger.error(f"Failed to record transition in graph: {e}", exc_info=True)

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
        logger.info(">>> _handle_plan_approved called")
        try:
            logger.info(">>> Decoding message...")
            event = json.loads(msg.data.decode())
            story_id = event.get("story_id")
            plan_id = event.get("plan_id")
            approved_by = event.get("approved_by")
            timestamp = event.get("timestamp")

            logger.info(f">>> Plan approved: {plan_id} for story {story_id} by {approved_by}")
            logger.info(f">>> Graph command available: {self.graph is not None}")

            # Record approval in graph
            if self.graph:
                logger.info(f">>> Attempting to save to Neo4j: {plan_id}")
                try:
                    entity_id = f"{plan_id}:{timestamp}"
                    logger.info(f">>> Entity ID: {entity_id}")
                    
                    await asyncio.to_thread(
                        self.graph.upsert_entity,
                        label="PlanApproval",
                        id=entity_id,
                        properties={
                            "story_id": story_id,
                            "plan_id": plan_id,
                            "approved_by": approved_by,
                            "timestamp": timestamp,
                        },
                    )
                    logger.info(f"✅ PlanApproval recorded in Neo4j: {plan_id} (entity_id={entity_id})")
                except Exception as e:
                    logger.error(f"❌ Failed to record approval in Neo4j: {e}", exc_info=True)
                    # Don't ACK if we couldn't save
                    await msg.nak()
                    return
            else:
                logger.warning(">>> Graph command is None, skipping Neo4j save")

            logger.info(f">>> About to ACK message for {plan_id}")
            await msg.ack()
            logger.info(f"✅ Message ACKed for plan {plan_id}")

        except Exception as e:
            logger.error(
                f"❌ Error handling plan approval: {e}",
                exc_info=True,
            )
            await msg.nak()

    async def stop(self):
        """Stop consuming events."""
        # JetStream subscriptions are automatically cleaned up when connection closes
        logger.info("Planning Events Consumer stopped")

