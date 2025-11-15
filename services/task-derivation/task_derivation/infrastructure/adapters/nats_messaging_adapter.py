"""NATS adapter for publishing task-derivation events, implementing MessagingPort."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from task_derivation.application.ports.messaging_port import MessagingPort
from task_derivation.domain.events.task_derivation_completed_event import (
    TaskDerivationCompletedEvent,
)
from task_derivation.domain.events.task_derivation_failed_event import (
    TaskDerivationFailedEvent,
)

logger = logging.getLogger(__name__)


class NATSMessagingAdapter(MessagingPort):
    """Concrete adapter for publishing task-derivation domain events to NATS."""

    def __init__(self, nats_client: Any) -> None:
        """Initialize adapter with NATS client.

        Args:
            nats_client: Connected nats.aio.client.Client instance

        Raises:
            ValueError: If nats_client is None
        """
        if not nats_client:
            raise ValueError("nats_client cannot be None")

        self._nats_client = nats_client

    async def publish_task_derivation_completed(
        self,
        event: TaskDerivationCompletedEvent,
    ) -> None:
        """Publish task derivation success event to NATS.

        Args:
            event: TaskDerivationCompletedEvent with task nodes and dependencies

        Raises:
            Exception: If NATS publish fails
        """
        try:
            payload = {
                "event_type": "task.derivation.completed",
                "plan_id": event.plan_id.value,
                "story_id": event.story_id.value,
                "role": event.role.value,
                "task_count": event.task_count,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            message = json.dumps(payload).encode("utf-8")
            await self._nats_client.publish("task.derivation.completed", message)

            logger.info(
                "Published task.derivation.completed for plan %s (tasks: %d)",
                event.plan_id.value,
                event.task_count,
            )

        except Exception as exc:
            logger.error(
                "Failed to publish task.derivation.completed event: %s",
                exc,
                exc_info=True,
            )
            raise

    async def publish_task_derivation_failed(
        self,
        event: TaskDerivationFailedEvent,
    ) -> None:
        """Publish task derivation failure event to NATS.

        Args:
            event: TaskDerivationFailedEvent with failure reason

        Raises:
            Exception: If NATS publish fails
        """
        try:
            payload = {
                "event_type": "task.derivation.failed",
                "plan_id": event.plan_id.value,
                "story_id": event.story_id.value,
                "reason": event.reason,
                "requires_manual_review": event.requires_manual_review,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            message = json.dumps(payload).encode("utf-8")
            await self._nats_client.publish("task.derivation.failed", message)

            logger.warning(
                "Published task.derivation.failed for plan %s: %s",
                event.plan_id.value,
                event.reason,
            )

        except Exception as exc:
            logger.error(
                "Failed to publish task.derivation.failed event: %s",
                exc,
                exc_info=True,
            )
            raise

