"""
Orchestration Events Consumer for Context Service.

Consumes events from Orchestrator Service to update context with
deliberation results and decisions.
"""

import asyncio
import json
import logging
import time
from typing import Any

from nats.aio.client import Client as NATS
from nats.js import JetStreamContext

logger = logging.getLogger(__name__)


class OrchestrationEventsConsumer:
    """Consumes orchestration events and updates context with decisions."""

    def __init__(
        self,
        nc: NATS,
        js: JetStreamContext,
        graph_command: Any,
        nats_publisher: Any = None,
    ):
        """
        Initialize Orchestration Events Consumer.

        Args:
            nc: NATS client
            js: JetStream context
            graph_command: Graph command store (Neo4j)
            nats_publisher: Optional publisher for context.updated events
        """
        self.nc = nc
        self.js = js
        self.graph = graph_command
        self.publisher = nats_publisher

    async def start(self):
        """Start consuming orchestration events."""
        try:
            # Subscribe to deliberation completed events
            await self.js.subscribe(
                "orchestration.deliberation.completed",
                queue="context-workers",
                cb=self._handle_deliberation_completed,
            )
            logger.info("✓ Subscribed to orchestration.deliberation.completed")

            # Subscribe to task dispatched events (for monitoring)
            await self.js.subscribe(
                "orchestration.task.dispatched",
                queue="context-workers",
                cb=self._handle_task_dispatched,
            )
            logger.info("✓ Subscribed to orchestration.task.dispatched")

            logger.info("✓ Orchestration Events Consumer started")

        except Exception as e:
            logger.error(f"Failed to start Orchestration Events Consumer: {e}")
            raise

    async def _handle_deliberation_completed(self, msg):
        """
        Handle deliberation completed events.

        When a deliberation completes, we persist the decisions made
        into the graph database and publish a context.updated event.
        """
        try:
            event = json.loads(msg.data.decode())
            story_id = event.get("story_id")
            task_id = event.get("task_id")
            decisions = event.get("decisions", [])
            timestamp = event.get("timestamp", int(time.time()))

            logger.info(
                f"Deliberation completed: {task_id} with {len(decisions)} decisions"
            )

            # Persist each decision to graph
            if self.graph and decisions:
                for decision in decisions:
                    try:
                        decision_id = decision.get("id") or f"DEC-{task_id}-{decisions.index(decision)}"
                        
                        await asyncio.to_thread(
                            self.graph.upsert_entity,
                            entity_type="Decision",
                            entity_id=decision_id,
                            properties={
                                "story_id": story_id,
                                "task_id": task_id,
                                "title": decision.get("title", ""),
                                "rationale": decision.get("rationale", ""),
                                "impact": decision.get("impact", ""),
                                "alternatives": json.dumps(decision.get("alternatives", [])),
                                "timestamp": timestamp,
                                "decision_type": decision.get("type", "TECHNICAL"),
                            },
                        )
                        logger.debug(f"✓ Persisted decision {decision_id}")

                    except Exception as e:
                        logger.error(f"Failed to persist decision {decision_id}: {e}")
                        # Continue with other decisions even if one fails

            # Publish context.updated event
            if self.publisher:
                try:
                    await self.publisher.publish_context_updated(
                        story_id=story_id,
                        version=timestamp,
                    )
                    logger.debug(f"✓ Published context.updated for {story_id}")
                except Exception as e:
                    logger.warning(f"Failed to publish context.updated: {e}")

            await msg.ack()
            logger.debug(f"✓ Processed deliberation completion for {task_id}")

        except Exception as e:
            logger.error(
                f"Error handling deliberation completed: {e}",
                exc_info=True,
            )
            await msg.nak()

    async def _handle_task_dispatched(self, msg):
        """
        Handle task dispatched events.

        Records when a task is dispatched to an agent for tracking
        and monitoring purposes.
        """
        try:
            event = json.loads(msg.data.decode())
            story_id = event.get("story_id")
            task_id = event.get("task_id")
            agent_id = event.get("agent_id")
            role = event.get("role")
            timestamp = event.get("timestamp", int(time.time()))

            logger.info(f"Task dispatched: {task_id} to agent {agent_id} ({role})")

            # Record dispatch in graph for audit trail
            if self.graph:
                try:
                    await asyncio.to_thread(
                        self.graph.upsert_entity,
                        entity_type="TaskDispatch",
                        entity_id=f"{task_id}:{timestamp}",
                        properties={
                            "story_id": story_id,
                            "task_id": task_id,
                            "agent_id": agent_id,
                            "role": role,
                            "timestamp": timestamp,
                            "status": "dispatched",
                        },
                    )
                except Exception as e:
                    logger.warning(f"Failed to record task dispatch: {e}")

            await msg.ack()
            logger.debug(f"✓ Processed task dispatch for {task_id}")

        except Exception as e:
            logger.error(
                f"Error handling task dispatched: {e}",
                exc_info=True,
            )
            await msg.nak()

    async def stop(self):
        """Stop consuming events."""
        logger.info("Orchestration Events Consumer stopped")

