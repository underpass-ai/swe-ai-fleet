"""
Agent Response Consumer for Orchestrator Service.

Consumes agent execution responses to track task completion and outcomes.

Refactored to follow Hexagonal Architecture:
- Uses MessagingPort instead of direct NATS publisher
- Publishes domain events (TaskCompletedEvent, TaskFailedEvent)
- No direct access to orchestrator service
"""

import asyncio
import json
import logging

from core.shared.events.infrastructure import parse_required_envelope
from services.orchestrator.domain.entities import (
    AgentCompletedResponse,
    AgentFailedResponse,
    AgentProgressUpdate,
)
from services.orchestrator.domain.events import TaskCompletedEvent, TaskFailedEvent
from services.orchestrator.domain.ports import MessagingPort

logger = logging.getLogger(__name__)


class OrchestratorAgentResponseConsumer:
    """Consumes agent responses to process task results.

    Following Hexagonal Architecture:
    - Uses MessagingPort for publishing events
    - Publishes domain events instead of raw dicts
    - No direct dependencies on orchestrator internals
    """

    def __init__(
        self,
        messaging: MessagingPort,
    ):
        """
        Initialize Orchestrator Agent Response Consumer.

        Following Hexagonal Architecture:
        - Only receives MessagingPort (no NATS client)
        - Fully decoupled from NATS infrastructure

        Args:
            messaging: Port for publishing events and subscriptions
        """
        self.messaging = messaging

    async def start(self):
        """Start consuming agent responses via MessagingPort."""
        try:
            # Use PULL subscriptions to allow multiple replicas (load balancing across pods)
            # This consumer publishes orchestration events (TaskCompletedEvent, TaskFailedEvent)
            # while DeliberationCollector tracks deliberation state
            import asyncio

            self._completed_sub = await self.messaging.pull_subscribe(
                subject="agent.response.completed",
                durable="orch-agent-response-completed-v3",
                stream="AGENT_RESPONSES",
            )
            logger.info("✓ Pull subscription created for agent.response.completed (DURABLE)")

            self._failed_sub = await self.messaging.pull_subscribe(
                subject="agent.response.failed",
                durable="orch-agent-response-failed-v3",
                stream="AGENT_RESPONSES",
            )
            logger.info("✓ Pull subscription created for agent.response.failed (DURABLE)")

            self._progress_sub = await self.messaging.pull_subscribe(
                subject="agent.response.progress",
                durable="orch-agent-response-progress-v3",
                stream="AGENT_RESPONSES",
            )
            logger.info("✓ Pull subscription created for agent.response.progress (DURABLE)")

            # Start background polling tasks
            self._tasks = [
                asyncio.create_task(self._poll_completed()),
                asyncio.create_task(self._poll_failed()),
                asyncio.create_task(self._poll_progress()),
            ]

            logger.info("✓ Orchestrator Agent Response Consumer started with DURABLE PULL consumers")

        except Exception as e:
            logger.error(f"Failed to start Orchestrator Agent Response Consumer: {e}")
            raise

    async def stop(self) -> None:
        """Stop the consumer and cancel all polling tasks."""
        logger.info("Stopping OrchestratorAgentResponseConsumer...")

        # Cancel all polling tasks
        for task in self._tasks:
            task.cancel()

        # Wait for all tasks to finish cancelling (CancelledError propagates naturally)
        await asyncio.gather(*self._tasks, return_exceptions=True)

        logger.info("✅ OrchestratorAgentResponseConsumer stopped")

    async def _poll_completed(self):  # pragma: no cover
        """Poll for agent.response.completed messages.

        Infinite background loop - runs until task is cancelled.
        The business logic is in _handle_agent_completed() which is unit tested.
        """
        try:
            while True:
                try:
                    messages = await self._completed_sub.fetch(batch=1, timeout=5.0)
                    for msg in messages:
                        await self._handle_agent_completed(msg)
                except TimeoutError:
                    logger.debug("⏱️  No completed responses (timeout), continuing...")
                    continue
                except Exception as e:
                    logger.error(f"Error polling completed responses: {e}", exc_info=True)
                    await asyncio.sleep(5.0)
        except asyncio.CancelledError:
            logger.info("_poll_completed task cancelled, shutting down...")
            raise

    async def _poll_failed(self):  # pragma: no cover
        """Poll for agent.response.failed messages.

        Infinite background loop - runs until task is cancelled.
        The business logic is in _handle_agent_failed() which is unit tested.
        """
        try:
            while True:
                try:
                    messages = await self._failed_sub.fetch(batch=1, timeout=5.0)
                    for msg in messages:
                        await self._handle_agent_failed(msg)
                except TimeoutError:
                    logger.debug("⏱️  No failed responses (timeout), continuing...")
                    continue
                except Exception as e:
                    logger.error(f"Error polling failed responses: {e}", exc_info=True)
                    await asyncio.sleep(5.0)
        except asyncio.CancelledError:
            logger.info("_poll_failed task cancelled, shutting down...")
            raise

    async def _poll_progress(self):  # pragma: no cover
        """Poll for agent.response.progress messages.

        Infinite background loop - runs until task is cancelled.
        The business logic is in _handle_agent_progress() which is unit tested.
        """
        try:
            while True:
                try:
                    messages = await self._progress_sub.fetch(batch=1, timeout=5.0)
                    for msg in messages:
                        await self._handle_agent_progress(msg)
                except TimeoutError:
                    logger.debug("⏱️  No progress updates (timeout), continuing...")
                    continue
                except Exception as e:
                    logger.error(f"Error polling progress updates: {e}", exc_info=True)
                    await asyncio.sleep(5.0)
        except asyncio.CancelledError:
            logger.info("_poll_progress task cancelled, shutting down...")
            raise

    async def _handle_agent_completed(self, msg):
        """
        Handle completed agent execution.

        When an agent completes a task, we:
        - Record the outcome
        - Update task status
        - Trigger deliberation if needed
        - Dispatch next task in queue
        """
        try:
            # Parse JSON payload
            data = json.loads(msg.data.decode())

            try:
                envelope = parse_required_envelope(data)
            except ValueError as e:
                logger.error(
                    f"Dropping agent.response.completed without valid EventEnvelope: {e}",
                    exc_info=True,
                )
                await msg.ack()
                return

            idempotency_key = envelope.idempotency_key
            correlation_id = envelope.correlation_id
            response_data = envelope.payload

            logger.debug(
                f"📥 [EventEnvelope] Received agent completed: "
                f"idempotency_key={idempotency_key[:16]}..., "
                f"correlation_id={correlation_id}, "
                f"event_type={envelope.event_type}, "
                f"producer={envelope.producer}"
            )

            # Log num_agents from NATS message for debugging
            num_agents_in_message = response_data.get("num_agents")
            task_id_for_log = response_data.get("task_id", "unknown")
            if num_agents_in_message is not None:
                logger.info(
                    f"[{task_id_for_log}] ✅ Found num_agents={num_agents_in_message} in NATS message"
                )
            else:
                logger.warning(
                    f"[{task_id_for_log}] ⚠️ num_agents NOT found in NATS message. "
                    f"Keys: {list(response_data.keys())}"
                )

            # Parse as domain entity (Tell, Don't Ask)
            response = AgentCompletedResponse.from_dict(response_data)

            logger.info(
                f"Agent completed: {response.agent_id} ({response.role}) finished task {response.task_id}. "
                f"correlation_id={correlation_id}, "
                f"idempotency_key={idempotency_key[:16]}..."
            )

            logger.info(
                f"Task {response.task_id} completed in {response.duration_ms}ms, "
                f"checks: {'✓' if response.checks_passed else '✗'}"
            )

            # IMPLEMENTATION STATUS: Basic event publishing implemented.
            # FUTURE ENHANCEMENTS needed:
            # - Update task status in orchestrator's task queue
            # - Trigger Deliberate RPC if deliberation needed
            # - Record results for metrics/analytics
            # - Dispatch next task if available (sequential execution)


            # Publish completion event using domain entity
            try:
                event = TaskCompletedEvent(
                    task_id=response.task_id,
                    story_id=response.story_id,
                    agent_id=response.agent_id,
                    role=response.role,
                    duration_ms=response.duration_ms,
                    checks_passed=response.checks_passed,
                    timestamp=response.timestamp,
                )
                await self.messaging.publish(
                    "orchestration.task.completed",
                    event
                )
                logger.debug(f"Published orchestration.task.completed for {response.task_id}")
            except Exception as e:
                logger.warning(f"Failed to publish task completion event: {e}")

            await msg.ack()
            logger.debug(f"✓ Processed agent completion for {response.task_id}")

        except Exception as e:
            logger.error(
                f"Error handling agent completion: {e}",
                exc_info=True,
            )
            await msg.nak()

    async def _handle_agent_failed(self, msg):
        """
        Handle failed agent execution.

        When an agent fails, we:
        - Record the failure
        - Analyze error type
        - Decide on retry strategy
        - Update task status
        """
        try:
            # Parse JSON payload
            data = json.loads(msg.data.decode())

            try:
                envelope = parse_required_envelope(data)
            except ValueError as e:
                logger.error(
                    f"Dropping agent.response.failed without valid EventEnvelope: {e}",
                    exc_info=True,
                )
                await msg.ack()
                return

            idempotency_key = envelope.idempotency_key
            correlation_id = envelope.correlation_id
            response_data = envelope.payload

            logger.debug(
                f"📥 [EventEnvelope] Received agent failed: "
                f"idempotency_key={idempotency_key[:16]}..., "
                f"correlation_id={correlation_id}, "
                f"event_type={envelope.event_type}, "
                f"producer={envelope.producer}"
            )

            # Parse as domain entity (Tell, Don't Ask)
            response = AgentFailedResponse.from_dict(response_data)

            logger.warning(
                f"Agent failed: {response.agent_id} ({response.role}) failed task "
                f"{response.task_id}: {response.error}. "
                f"correlation_id={correlation_id}, "
                f"idempotency_key={idempotency_key[:16]}..."
            )

            # IMPLEMENTATION STATUS: Basic failure event publishing implemented.
            # FUTURE ENHANCEMENTS needed:
            # - Analyze error type (transient vs permanent)
            # - Implement retry strategy with exponential backoff
            # - Update task status in orchestrator queue
            # - Notify stakeholders for critical failures
            # - DLQ handling for permanent failures


            # Publish failure event using domain entity
            try:
                event = TaskFailedEvent(
                    task_id=response.task_id,
                    story_id=response.story_id,
                    agent_id=response.agent_id,
                    role=response.role,
                    error=response.error,
                    error_type=response.error_type,
                    timestamp=response.timestamp,
                )
                await self.messaging.publish(
                    "orchestration.task.failed",
                    event
                )
                logger.debug(f"Published orchestration.task.failed for {response.task_id}")
            except Exception as e:
                logger.warning(f"Failed to publish task failure event: {e}")

            await msg.ack()
            logger.debug(f"✓ Processed agent failure for {response.task_id}")

        except Exception as e:
            logger.error(
                f"Error handling agent failure: {e}",
                exc_info=True,
            )
            await msg.nak()

    async def _handle_agent_progress(self, msg):
        """
        Handle agent progress updates.

        Progress updates allow us to:
        - Monitor long-running tasks
        - Detect stuck agents
        - Provide real-time feedback to UI
        """
        try:
            # Parse JSON payload
            data = json.loads(msg.data.decode())

            try:
                envelope = parse_required_envelope(data)
            except ValueError as e:
                logger.error(
                    f"Dropping agent.response.progress without valid EventEnvelope: {e}",
                    exc_info=True,
                )
                await msg.ack()
                return

            idempotency_key = envelope.idempotency_key
            correlation_id = envelope.correlation_id
            progress_data = envelope.payload

            logger.debug(
                f"📥 [EventEnvelope] Received agent progress: "
                f"idempotency_key={idempotency_key[:16]}..., "
                f"correlation_id={correlation_id}, "
                f"event_type={envelope.event_type}"
            )

            # Parse as domain entity (Tell, Don't Ask)
            progress = AgentProgressUpdate.from_dict(progress_data)

            logger.debug(
                f"Agent progress: {progress.agent_id} on task {progress.task_id} - "
                f"{progress.progress_pct}%: {progress.message}"
            )

            # IMPLEMENTATION STATUS: Basic progress logging implemented.
            # FUTURE ENHANCEMENTS needed:
            # - Store progress state for real-time queries
            # - Detect stalled tasks (timeout without progress updates)
            # - Forward to Gateway via SSE for UI updates
            # - Aggregate progress metrics for analytics

            # For high-frequency progress updates, we just ack without publishing
            await msg.ack()

        except Exception as e:
            logger.error(
                f"Error handling agent progress: {e}",
                exc_info=True,
            )
            await msg.nak()

