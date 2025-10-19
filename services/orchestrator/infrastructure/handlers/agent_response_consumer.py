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
            # NOTE: agent.response.completed and agent.response.failed are handled by
            # DeliberationResultCollector (durable consumer) to track deliberation state.
            # This consumer only handles progress updates (ephemeral, high frequency).
            
            await self.messaging.subscribe(
                subject="agent.response.progress",
                handler=self._handle_agent_progress,
                queue_group="orchestrator-workers",
            )
            logger.info("✓ Subscribed to agent.response.progress")

            logger.info("✓ Orchestrator Agent Response Consumer started (progress only)")

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
            # Parse as domain entity (Tell, Don't Ask)
            response_data = json.loads(msg.data.decode())
            response = AgentCompletedResponse.from_dict(response_data)

            logger.info(
                f"Agent completed: {response.agent_id} ({response.role}) finished task {response.task_id}"
            )
            
            logger.info(
                f"Task {response.task_id} completed in {response.duration_ms}ms, "
                f"checks: {'✓' if response.checks_passed else '✗'}"
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
            # Parse as domain entity (Tell, Don't Ask)
            response_data = json.loads(msg.data.decode())
            response = AgentFailedResponse.from_dict(response_data)

            logger.warning(
                f"Agent failed: {response.agent_id} ({response.role}) failed task "
                f"{response.task_id}: {response.error}"
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
            # Parse as domain entity (Tell, Don't Ask)
            progress_data = json.loads(msg.data.decode())
            progress = AgentProgressUpdate.from_dict(progress_data)

            logger.debug(
                f"Agent progress: {progress.agent_id} on task {progress.task_id} - "
                f"{progress.progress_pct}%: {progress.message}"
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

