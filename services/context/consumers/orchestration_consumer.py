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

# Import use cases
from core.context.usecases.project_decision import ProjectDecisionUseCase
from core.context.usecases.update_task_status import UpdateTaskStatusUseCase
from core.shared.events.infrastructure import parse_required_envelope
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

        # Initialize use cases
        self.project_decision = ProjectDecisionUseCase(writer=graph_command)
        self.update_subtask_status = UpdateTaskStatusUseCase(writer=graph_command)

    async def start(self):
        """Start consuming orchestration events with DURABLE PULL consumers."""
        try:
            # Create PULL subscriptions instead of PUSH
            # This allows multiple pods to share the same durable consumer

            # Pull consumer for deliberation completed
            self._delib_sub = await self.js.pull_subscribe(
                subject="orchestration.deliberation.completed",
                durable="context-orch-deliberation-completed",
                stream="ORCHESTRATOR_EVENTS",
            )
            logger.info("✓ Pull subscription created for orchestration.deliberation.completed (DURABLE)")

            # Pull consumer for task dispatched
            self._dispatch_sub = await self.js.pull_subscribe(
                subject="orchestration.task.dispatched",
                durable="context-orch-task-dispatched",
                stream="ORCHESTRATOR_EVENTS",
            )
            logger.info("✓ Pull subscription created for orchestration.task.dispatched (DURABLE)")

            # Start background tasks to fetch and process messages
            import asyncio
            self._tasks = [
                asyncio.create_task(self._poll_deliberation_completed()),
                asyncio.create_task(self._poll_task_dispatched()),
            ]

            logger.info("✓ Orchestration Events Consumer started with DURABLE PULL consumers")

        except Exception as e:
            logger.error(f"Failed to start Orchestration Events Consumer: {e}", exc_info=True)
            raise

    async def _poll_deliberation_completed(self):
        """Poll for deliberation completed messages."""
        while True:
            try:
                msgs = await self._delib_sub.fetch(batch=1, timeout=5)
                for msg in msgs:
                    await self._handle_deliberation_completed(msg)
            except TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error polling deliberation completed: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _poll_task_dispatched(self):
        """Poll for task dispatched messages."""
        while True:
            try:
                msgs = await self._dispatch_sub.fetch(batch=1, timeout=5)
                for msg in msgs:
                    await self._handle_task_dispatched(msg)
            except TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error polling task dispatched: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _handle_deliberation_completed(self, msg):
        """
        Handle deliberation completed events.

        When a deliberation completes, we persist the decisions made
        into the graph database and publish a context.updated event.
        """
        try:
            # Parse JSON payload
            data = json.loads(msg.data.decode())

            try:
                envelope = parse_required_envelope(data)
            except ValueError as e:
                logger.error(
                    f"Dropping orchestration.deliberation.completed without valid EventEnvelope: {e}",
                    exc_info=True,
                )
                await msg.ack()
                return

            idempotency_key = envelope.idempotency_key
            correlation_id = envelope.correlation_id
            event = envelope.payload

            logger.debug(
                f"📥 [EventEnvelope] Received deliberation completed: "
                f"idempotency_key={idempotency_key[:16]}..., "
                f"correlation_id={correlation_id}, "
                f"event_type={envelope.event_type}, "
                f"producer={envelope.producer}"
            )

            story_id = event.get("story_id")
            task_id = event.get("task_id")
            decisions = event.get("decisions", [])
            timestamp = event.get("timestamp", int(time.time()))

            logger.info(
                f"Deliberation completed: {task_id} with {len(decisions)} decisions. "
                f"correlation_id={correlation_id}, "
                f"idempotency_key={idempotency_key[:16]}..."
            )

            # Persist each decision using domain use case
            if decisions:
                for decision in decisions:
                    try:
                        decision_id = decision.get("id") or f"DEC-{task_id}-{decisions.index(decision)}"

                        # Build payload for use case
                        payload = {
                            "node_id": decision_id,
                            "kind": decision.get("type", "TECHNICAL"),
                            "summary": decision.get("rationale", ""),
                            # If decision affects a subtask, include it
                            "sub_id": decision.get("affected_subtask"),
                        }

                        # Call use case in thread pool (graph operations are sync)
                        await asyncio.to_thread(
                            self.project_decision.execute,
                            payload
                        )
                        logger.debug(f"✓ Persisted decision {decision_id} via use case")

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
            # Parse JSON payload
            data = json.loads(msg.data.decode())

            try:
                envelope = parse_required_envelope(data)
            except ValueError as e:
                logger.error(
                    f"Dropping orchestration.task.dispatched without valid EventEnvelope: {e}",
                    exc_info=True,
                )
                await msg.ack()
                return

            idempotency_key = envelope.idempotency_key
            correlation_id = envelope.correlation_id
            event = envelope.payload

            logger.debug(
                f"📥 [EventEnvelope] Received task dispatched: "
                f"idempotency_key={idempotency_key[:16]}..., "
                f"correlation_id={correlation_id}, "
                f"event_type={envelope.event_type}, "
                f"producer={envelope.producer}"
            )

            story_id = event.get("story_id")
            task_id = event.get("task_id")
            agent_id = event.get("agent_id")
            role = event.get("role")
            timestamp = event.get("timestamp", int(time.time()))

            logger.info(
                f"Task dispatched: {task_id} to agent {agent_id} ({role}). "
                f"correlation_id={correlation_id}, "
                f"idempotency_key={idempotency_key[:16]}..."
            )

            # Update subtask status to IN_PROGRESS using use case
            try:
                payload = {
                    "sub_id": task_id,
                    "status": "IN_PROGRESS",
                }

                await asyncio.to_thread(
                    self.update_subtask_status.execute,
                    payload
                )
                logger.debug(f"✓ Updated subtask {task_id} status to IN_PROGRESS")
            except Exception as e:
                logger.warning(f"Failed to update subtask status: {e}")

            # Also record dispatch event in graph for audit trail
            try:
                await asyncio.to_thread(
                    self.graph.upsert_entity,
                    label="TaskDispatch",  # ← CORRECTED: parameter name
                    id=f"{task_id}:{timestamp}",  # ← CORRECTED: parameter name
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
                logger.warning(f"Failed to record task dispatch event: {e}")

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
        await asyncio.sleep(0)  # Make function truly async
        logger.info("Orchestration Events Consumer stopped")

