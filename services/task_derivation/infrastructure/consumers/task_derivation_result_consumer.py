"""NATS consumer for derivation results (`agent.response.completed`)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from task_derivation.application.ports.messaging_port import MessagingPort
from task_derivation.application.usecases.process_task_derivation_result_usecase import (
    ProcessTaskDerivationResultUseCase,
)
from task_derivation.domain.events.task_derivation_failed_event import (
    TaskDerivationFailedEvent,
)
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.infrastructure.handlers.process_result_handler import (
    process_result_handler,
)

logger = logging.getLogger(__name__)


class TaskDerivationResultConsumer:
    """Inbound adapter for Ray execution results."""

    SUBJECT = "agent.response.completed"
    DURABLE = "task-derivation-result-consumer"
    STREAM = "AGENT_RESPONSES"

    def __init__(
        self,
        *,
        nats_client: Any,
        jetstream: Any,
        process_usecase: ProcessTaskDerivationResultUseCase,
        messaging_port: MessagingPort,
        max_deliveries: int = 3,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Initialize consumer.

        Args:
            nats_client: NATS client instance
            jetstream: NATS JetStream instance
            process_usecase: ProcessTaskDerivationResultUseCase instance (injected)
            messaging_port: MessagingPort for publishing failure events
            max_deliveries: Maximum delivery attempts before ack
            clock: Clock function for timestamps (default: UTC now)
        """
        self._nc = nats_client
        self._js = jetstream
        self._process_usecase = process_usecase
        self._messaging = messaging_port
        self._max_deliveries = max_deliveries
        self._clock = clock or (lambda: datetime.now(UTC))
        self._subscription = None
        self._polling_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._subscription = await self._js.pull_subscribe(
            subject=self.SUBJECT,
            durable=self.DURABLE,
            stream=self.STREAM,
        )
        self._polling_task = asyncio.create_task(self._poll())
        logger.info("TaskDerivationResultConsumer subscribed to %s", self.SUBJECT)

    async def stop(self) -> None:
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                logger.info("TaskDerivationResultConsumer stopped")
                raise
        logger.info("TaskDerivationResultConsumer stopped")

    async def _poll(self) -> None:
        while True:
            try:
                messages = await self._subscription.fetch(batch=1, timeout=5)
                for msg in messages:
                    await self._handle_message(msg)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Error polling derivation results: %s", exc, exc_info=True)
                await asyncio.sleep(5)

    async def _handle_message(self, msg: Any) -> None:
        """Handle a single NATS message.

        Following Hexagonal Architecture:
        - Consumer handles infrastructure concerns (polling, ack/nak)
        - Handler handles domain boundary (payload → VO → use case)
        - Separation of concerns: consumer ≠ handler

        Args:
            msg: NATS message object
        """
        # Extract delivery count from NATS message metadata
        try:
            deliveries = msg.metadata.num_delivered
        except AttributeError:
            deliveries = 1

        payload: dict[str, Any] | None = None
        try:
            # Parse JSON payload
            payload = json.loads(msg.data.decode("utf-8"))

            # Delegate to handler (handler uses mapper and calls use case)
            await process_result_handler(payload, self._process_usecase)

            # Success: acknowledge message
            await msg.ack()

        except ValueError as exc:
            # Invalid payload: publish failure event and drop message
            await self._publish_failure_from_consumer(payload or {}, str(exc))
            await msg.ack()  # Drop invalid message

        except Exception as exc:
            # Error: retry or drop based on delivery count
            if deliveries >= self._max_deliveries:
                logger.error(
                    "Max deliveries exceeded for derivation result: %s", exc
                )
                await msg.ack()  # Drop after max retries
            else:
                logger.warning(
                    "Error processing derivation result (delivery %s): %s",
                    deliveries,
                    exc,
                )
                await msg.nak()  # Retry

    def _extract_identifiers(
        self,
        payload: dict[str, Any],
    ) -> tuple[PlanId, StoryId]:
        plan_raw = payload.get("plan_id")
        story_raw = payload.get("story_id")

        if not plan_raw:
            raise ValueError("plan_id missing from derivation result payload")
        if not story_raw:
            raise ValueError("story_id missing from derivation result payload")

        return PlanId(str(plan_raw)), StoryId(str(story_raw))

    async def _publish_failure_from_consumer(
        self,
        payload: dict[str, Any],
        reason: str,
    ) -> None:
        try:
            plan_id, story_id = self._extract_identifiers(payload)
        except ValueError:
            logger.error("Cannot publish failure event: missing identifiers")
            return

        event = TaskDerivationFailedEvent(
            plan_id=plan_id,
            story_id=story_id,
            reason=reason,
            requires_manual_review=True,
            occurred_at=self._clock(),
        )
        await self._messaging.publish_task_derivation_failed(event)

