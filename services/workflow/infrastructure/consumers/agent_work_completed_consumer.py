"""Agent work completed consumer.

Consumes agent.work.completed events and executes workflow actions.
Following Hexagonal Architecture.
"""

import asyncio
import json
import logging
from datetime import datetime

from core.shared.domain import Action, ActionEnum
from nats.aio.client import Client as NATS
from nats.js import JetStreamContext

from services.workflow.application.usecases.execute_workflow_action_usecase import (
    ExecuteWorkflowActionUseCase,
)
from services.workflow.domain.value_objects.nats_subjects import NatsSubjects
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.task_id import TaskId

logger = logging.getLogger(__name__)


class AgentWorkCompletedConsumer:
    """NATS consumer for agent.work.completed events.

    Listens to agent work completion and advances workflow state.
    Uses PULL subscription (supports multiple replicas).

    Event schema:
    {
        "task_id": "task-001",
        "action": "commit_code",
        "actor_role": "developer",
        "timestamp": "2025-11-05T10:30:00Z",
        "feedback": "Optional feedback"
    }

    Following Hexagonal Architecture:
    - Infrastructure layer (NATS-specific)
    - Calls application use case (ExecuteWorkflowActionUseCase)
    - Handles deserialization (str → domain objects)
    """

    def __init__(
        self,
        nats_client: NATS,
        jetstream: JetStreamContext,
        execute_workflow_action: ExecuteWorkflowActionUseCase,
    ) -> None:
        """Initialize consumer.

        Args:
            nats_client: NATS client
            jetstream: JetStream context
            execute_workflow_action: Use case for workflow action execution
        """
        self._nats = nats_client
        self._js = jetstream
        self._execute_workflow_action = execute_workflow_action
        self._subscription = None
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """Start consuming agent.work.completed events.

        Uses PULL subscription:
        - Durable: workflow-agent-work-completed-v1
        - Stream: AGENT_WORK
        - Subject: agent.work.completed
        - Multiple replicas supported (queue-group-like behavior)
        """
        logger.info("Starting AgentWorkCompletedConsumer (PULL subscription)...")

        # PULL subscription (supports multiple replicas)
        self._subscription = await self._js.pull_subscribe(
            subject=str(NatsSubjects.AGENT_WORK_COMPLETED),
            durable="workflow-agent-work-completed-v1",
            stream="AGENT_WORK",
        )

        # Start background polling task
        task = asyncio.create_task(self._poll_messages())
        self._tasks.append(task)

        logger.info("✅ AgentWorkCompletedConsumer started (PULL mode)")

    async def stop(self) -> None:
        """Stop consumer gracefully."""
        logger.info("Stopping AgentWorkCompletedConsumer...")

        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete cancellation
        await asyncio.gather(*self._tasks, return_exceptions=True)

        logger.info("✅ AgentWorkCompletedConsumer stopped")

    async def _poll_messages(self):  # pragma: no cover
        """Poll for messages (infinite background loop).

        Marked as no cover: Infinite loop for production.
        Business logic in _handle_message() is unit tested.
        """
        try:
            while True:
                try:
                    # Fetch 10 messages, wait max 5 seconds
                    messages = await self._subscription.fetch(batch=10, timeout=5)

                    for msg in messages:
                        await self._handle_message(msg)
                        await msg.ack()

                except TimeoutError:
                    # No messages available, continue polling
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Error polling messages: {e}", exc_info=True)
                    await asyncio.sleep(1)  # Backoff on error

        except asyncio.CancelledError:
            logger.info("_poll_messages task cancelled, shutting down...")
            raise

    async def _handle_message(self, msg) -> None:
        """Handle agent.work.completed message.

        Deserializes event and calls use case.
        This method contains business logic and IS unit tested.

        Args:
            msg: NATS message
        """
        try:
            # Deserialize event payload
            payload = json.loads(msg.data.decode("utf-8"))

            # Extract fields (fail-fast if missing)
            task_id_str = payload["task_id"]
            action_str = payload["action"]
            actor_role_str = payload["actor_role"]
            timestamp_str = payload["timestamp"]
            feedback = payload.get("feedback")

            # Convert to domain objects (infrastructure responsibility)
            task_id = TaskId(task_id_str)
            action = Action(value=ActionEnum(action_str))
            actor_role = Role(actor_role_str)
            timestamp = datetime.fromisoformat(timestamp_str)

            # Execute workflow action via use case
            new_state = await self._execute_workflow_action.execute(
                task_id=task_id,
                action=action,
                actor_role=actor_role,
                timestamp=timestamp,
                feedback=feedback,
            )

            logger.info(
                f"✅ Workflow action executed: {task_id} "
                f"{action.value.value} by {actor_role} → {new_state.current_state.value}"
            )

        except KeyError as e:
            logger.error(f"Missing required field in event: {e}", exc_info=True)
            # Don't ack message with missing fields (will retry)
            raise

        except ValueError as e:
            logger.error(f"Invalid data in event: {e}", exc_info=True)
            # Invalid data = business error, log and continue (ack message)
            # Don't retry invalid data forever

        except Exception as e:
            logger.error(f"Error handling workflow event: {e}", exc_info=True)
            # Unexpected error, don't ack (will retry)
            raise

