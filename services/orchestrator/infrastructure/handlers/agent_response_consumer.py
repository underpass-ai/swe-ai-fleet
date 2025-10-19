"""
Agent Response Consumer for Orchestrator Service.

Consumes agent execution responses to track task completion and outcomes.

Refactored to follow Hexagonal Architecture:
- Uses MessagingPort instead of direct NATS publisher
- Publishes domain events (TaskCompletedEvent, TaskFailedEvent)
- No direct access to orchestrator service
"""

import json
import logging

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
            # Subscribe via MessagingPort (Hexagonal Architecture)
            await self.messaging.subscribe(
                subject="agent.response.completed",
                handler=self._handle_agent_completed,
                queue_group="orchestrator-workers",
            )
            logger.info("✓ Subscribed to agent.response.completed")

            await self.messaging.subscribe(
                subject="agent.response.failed",
                handler=self._handle_agent_failed,
                queue_group="orchestrator-workers",
            )
            logger.info("✓ Subscribed to agent.response.failed")

            await self.messaging.subscribe(
                subject="agent.response.progress",
                handler=self._handle_agent_progress,
                queue_group="orchestrator-workers",
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

            # Publish completion event using domain entity
            try:
                event = TaskCompletedEvent(
                    task_id=task_id,
                    story_id=story_id,
                    agent_id=agent_id,
                    role=role,
                    duration_ms=duration_ms,
                    checks_passed=checks_passed,
                    timestamp=timestamp,
                )
                await self.messaging.publish(
                    "orchestration.task.completed",
                    event
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

            # Publish failure event using domain entity
            try:
                event = TaskFailedEvent(
                    task_id=task_id,
                    story_id=story_id,
                    agent_id=agent_id,
                    role=role,
                    error=error,
                    error_type=error_type,
                    timestamp=timestamp,
                )
                await self.messaging.publish(
                    "orchestration.task.failed",
                    event
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

