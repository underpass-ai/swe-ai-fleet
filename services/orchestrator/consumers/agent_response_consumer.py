"""
Agent Response Consumer for Orchestrator Service.

Consumes agent execution responses to track task completion and outcomes.
"""

import json
import logging
from typing import Any

from nats.aio.client import Client as NATS
from nats.js import JetStreamContext

logger = logging.getLogger(__name__)


class OrchestratorAgentResponseConsumer:
    """Consumes agent responses to process task results."""

    def __init__(
        self,
        nc: NATS,
        js: JetStreamContext,
        orchestrator_service: Any,
        nats_publisher: Any = None,
    ):
        """
        Initialize Orchestrator Agent Response Consumer.

        Args:
            nc: NATS client
            js: JetStream context
            orchestrator_service: OrchestratorServiceServicer instance
            nats_publisher: Optional publisher for orchestration events
        """
        self.nc = nc
        self.js = js
        self.orchestrator = orchestrator_service
        self.publisher = nats_publisher

    async def start(self):
        """Start consuming agent responses."""
        try:
            # Subscribe to completed agent responses
            await self.js.subscribe(
                "agent.response.completed",
                queue="orchestrator-workers",
                cb=self._handle_agent_completed,
            )
            logger.info("✓ Subscribed to agent.response.completed")

            # Subscribe to failed agent responses
            await self.js.subscribe(
                "agent.response.failed",
                queue="orchestrator-workers",
                cb=self._handle_agent_failed,
            )
            logger.info("✓ Subscribed to agent.response.failed")

            # Subscribe to progress updates
            await self.js.subscribe(
                "agent.response.progress",
                queue="orchestrator-workers",
                cb=self._handle_agent_progress,
            )
            logger.info("✓ Subscribed to agent.response.progress")

            logger.info("✓ Orchestrator Agent Response Consumer started")

        except Exception as e:
            logger.error(f"Failed to start Orchestrator Agent Response Consumer: {e}")
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
            response = json.loads(msg.data.decode())
            task_id = response.get("task_id")
            agent_id = response.get("agent_id")
            story_id = response.get("story_id")
            role = response.get("role")
            output = response.get("output", {})
            timestamp = response.get("timestamp")

            logger.info(
                f"Agent completed: {agent_id} ({role}) finished task {task_id}"
            )

            # Extract key metrics
            duration_ms = output.get("duration_ms", 0)
            checks_passed = output.get("checks_passed", True)
            
            logger.info(
                f"Task {task_id} completed in {duration_ms}ms, "
                f"checks: {'✓' if checks_passed else '✗'}"
            )

            # TODO: Implement completion handling
            # This would:
            # 1. Update task status in orchestrator's task queue
            # 2. If deliberation needed, trigger Deliberate RPC
            # 3. Record results for metrics
            # 4. Publish orchestration.task.completed event
            # 5. Dispatch next task if available

            # Publish completion event
            if self.publisher:
                try:
                    await self.publisher.publish(
                        "orchestration.task.completed",
                        json.dumps({
                            "task_id": task_id,
                            "story_id": story_id,
                            "agent_id": agent_id,
                            "role": role,
                            "duration_ms": duration_ms,
                            "checks_passed": checks_passed,
                            "timestamp": timestamp,
                        }).encode(),
                    )
                    logger.debug(f"Published orchestration.task.completed for {task_id}")
                except Exception as e:
                    logger.warning(f"Failed to publish task completion event: {e}")

            await msg.ack()
            logger.debug(f"✓ Processed agent completion for {task_id}")

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
            response = json.loads(msg.data.decode())
            task_id = response.get("task_id")
            agent_id = response.get("agent_id")
            story_id = response.get("story_id")
            role = response.get("role")
            error = response.get("error", "Unknown error")
            error_type = response.get("error_type", "UNKNOWN")
            timestamp = response.get("timestamp")

            logger.warning(
                f"Agent failed: {agent_id} ({role}) failed task {task_id}: {error}"
            )

            # TODO: Implement failure handling
            # This would:
            # 1. Analyze error type (transient vs permanent)
            # 2. Decide on retry (with backoff) or abandon
            # 3. Update task status
            # 4. Notify stakeholders if critical
            # 5. Publish orchestration.task.failed event

            # Publish failure event
            if self.publisher:
                try:
                    await self.publisher.publish(
                        "orchestration.task.failed",
                        json.dumps({
                            "task_id": task_id,
                            "story_id": story_id,
                            "agent_id": agent_id,
                            "role": role,
                            "error": error,
                            "error_type": error_type,
                            "timestamp": timestamp,
                        }).encode(),
                    )
                    logger.debug(f"Published orchestration.task.failed for {task_id}")
                except Exception as e:
                    logger.warning(f"Failed to publish task failure event: {e}")

            await msg.ack()
            logger.debug(f"✓ Processed agent failure for {task_id}")

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
            progress = json.loads(msg.data.decode())
            task_id = progress.get("task_id")
            agent_id = progress.get("agent_id")
            progress_pct = progress.get("progress_pct", 0)
            message = progress.get("message", "")
            timestamp = progress.get("timestamp")

            logger.debug(
                f"Agent progress: {agent_id} on task {task_id} - {progress_pct}%: {message}"
            )

            # TODO: Implement progress tracking
            # This would:
            # 1. Update task progress in real-time
            # 2. Detect stalled tasks (no progress updates)
            # 3. Forward to Gateway for SSE
            
            # For high-frequency progress updates, we just ack without publishing
            await msg.ack()

        except Exception as e:
            logger.error(
                f"Error handling agent progress: {e}",
                exc_info=True,
            )
            await msg.nak()

    async def stop(self):
        """Stop consuming events."""
        logger.info("Orchestrator Agent Response Consumer stopped")

