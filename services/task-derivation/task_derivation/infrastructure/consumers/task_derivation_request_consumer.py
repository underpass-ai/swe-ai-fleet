"""NATS consumer for `task.derivation.requested` events."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from task_derivation.application.usecases.derive_tasks_usecase import (
    DeriveTasksUseCase,
)
from task_derivation.domain.value_objects.task_derivation.requests.task_derivation_request import (
    TaskDerivationRequest,
)
from task_derivation.infrastructure.mappers.task_derivation_request_mapper import (
    TaskDerivationRequestMapper,
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
        mapper: TaskDerivationRequestMapper | None = None,
        max_deliveries: int = 3,
    ) -> None:
        self._nats_client = nats_client
        self._jetstream = jetstream
        self._derive_tasks = derive_tasks_usecase
        self._mapper = mapper or TaskDerivationRequestMapper()
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
                pass
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
                break
            except Exception as exc:
                logger.error("Error fetching derivation requests: %s", exc, exc_info=True)
                await asyncio.sleep(5)

    async def _handle_message(self, msg: Any) -> None:
        deliveries = getattr(getattr(msg, "metadata", None), "num_delivered", 1)
        try:
            payload = json.loads(msg.data.decode("utf-8"))
            request = self._mapper.from_event(payload)
            await self._derive_tasks.execute(request)
            await msg.ack()
        except ValueError as exc:
            logger.error("Dropping invalid derivation request: %s", exc)
            await msg.ack()
        except Exception as exc:
            if deliveries >= self.max_deliveries:
                logger.error(
                    "Max deliveries exceeded for derivation request message: %s", exc
                )
                await msg.ack()
            else:
                logger.warning(
                    "Error processing derivation request (delivery %s): %s",
                    deliveries,
                    exc,
                )
                await msg.nak()

