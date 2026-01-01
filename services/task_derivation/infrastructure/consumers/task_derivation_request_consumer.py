"""NATS consumer for `task.derivation.requested` events."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from core.shared.events.infrastructure import parse_required_envelope
from task_derivation.application.usecases.derive_tasks_usecase import (
    DeriveTasksUseCase,
)
from task_derivation.infrastructure.handlers.derive_tasks_handler import (
    derive_tasks_handler,
)
from task_derivation.infrastructure.nats_subjects import (
    TaskDerivationRequestSubjects,
)

logger = logging.getLogger(__name__)


class TaskDerivationRequestConsumer:
    """Inbound adapter: listens to `task.derivation.requested` events."""

    def __init__(
        self,
        nats_client: Any,
        jetstream: Any,
        derive_tasks_usecase: DeriveTasksUseCase,
        max_deliveries: int = 3,
    ) -> None:
        """Initialize consumer.

        Args:
            nats_client: NATS client instance
            jetstream: NATS JetStream instance
            derive_tasks_usecase: DeriveTasksUseCase instance (injected)
            max_deliveries: Maximum delivery attempts before ack
        """
        self._nats_client = nats_client
        self._jetstream = jetstream
        self._derive_tasks_usecase = derive_tasks_usecase
        self._max_deliveries = max_deliveries
        self._subscription: Any | None = None
        self._polling_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start pull subscription and polling loop."""
        self._subscription = await self._jetstream.pull_subscribe(
            subject=TaskDerivationRequestSubjects.SUBJECT,
            durable=TaskDerivationRequestSubjects.DURABLE,
            stream=TaskDerivationRequestSubjects.STREAM,
        )
        self._polling_task = asyncio.create_task(self._poll())
        logger.info(
            "TaskDerivationRequestConsumer subscribed to %s",
            TaskDerivationRequestSubjects.SUBJECT,
        )

    async def stop(self) -> None:
        """Stop polling loop gracefully."""
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                logger.info("TaskDerivationRequestConsumer polling task cancelled")
                raise  # Re-raise CancelledError to properly propagate cancellation

        logger.info("TaskDerivationRequestConsumer stopped")

    async def _poll(self) -> None:
        while True:
            try:
                messages = await self._subscription.fetch(batch=1, timeout=5)
                for msg in messages:
                    await self._handle_message(msg)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info("TaskDerivationRequestConsumer polling loop cancelled")
                raise  # Re-raise CancelledError to properly propagate cancellation
            except Exception as exc:
                logger.error("Error fetching derivation requests: %s", exc, exc_info=True)
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

        try:
            # Parse JSON payload
            data = json.loads(msg.data.decode("utf-8"))

            # Require EventEnvelope (no legacy fallback)
            envelope = parse_required_envelope(data)
            idempotency_key = envelope.idempotency_key
            correlation_id = envelope.correlation_id
            payload = envelope.payload

            logger.debug(
                "📥 [EventEnvelope] Received task derivation request: "
                "idempotency_key=%s..., correlation_id=%s, event_type=%s, producer=%s",
                idempotency_key[:16],
                correlation_id,
                envelope.event_type,
                envelope.producer,
            )

            # Delegate to handler (handler uses mapper and calls use case)
            await derive_tasks_handler(payload, self._derive_tasks_usecase)

            logger.info(
                "✅ Task derivation request processed. "
                "correlation_id=%s, idempotency_key=%s",
                correlation_id,
                idempotency_key[:16] + "...",
            )

            # Success: acknowledge message
            await msg.ack()

        except ValueError as exc:
            # Invalid envelope / invalid payload: drop message (don't retry)
            logger.error("Dropping invalid derivation request: %s", exc, exc_info=True)
            await msg.ack()

        except Exception as exc:
            # Error: retry or drop based on delivery count
            if deliveries >= self._max_deliveries:
                logger.error(
                    "Max deliveries exceeded for derivation request message: %s", exc
                )
                await msg.ack()  # Drop after max retries
            else:
                logger.warning(
                    "Error processing derivation request (delivery %s): %s",
                    deliveries,
                    exc,
                )
                await msg.nak()  # Retry

