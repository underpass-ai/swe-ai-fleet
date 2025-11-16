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
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.infrastructure.mappers.llm_task_derivation_mapper import (
    LLMTaskDerivationMapper,
)

logger = logging.getLogger(__name__)


class TaskDerivationResultConsumer:
    """Inbound adapter for Ray execution results."""

    SUBJECT = "agent.response.completed"
    DURABLE = "task-derivation-result-consumer"
    STREAM = "agent_responses"

    def __init__(
        self,
        *,
        nats_client: Any,
        jetstream: Any,
        process_usecase: ProcessTaskDerivationResultUseCase,
        messaging_port: MessagingPort,
        llm_mapper: LLMTaskDerivationMapper | None = None,
        max_deliveries: int = 3,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._nc = nats_client
        self._js = jetstream
        self._process = process_usecase
        self._messaging = messaging_port
        self._llm_mapper = llm_mapper or LLMTaskDerivationMapper()
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
                pass
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
                break
            except Exception as exc:
                logger.error("Error polling derivation results: %s", exc, exc_info=True)
                await asyncio.sleep(5)

    async def _handle_message(self, msg: Any) -> None:
        # Extract delivery count from NATS message metadata
        try:
            deliveries = msg.metadata.num_delivered
        except AttributeError:
            deliveries = 1

        payload: dict[str, Any] | None = None
        try:
            payload = json.loads(msg.data.decode("utf-8"))
            plan_id, story_id = self._extract_identifiers(payload)
            role = ContextRole(payload.get("role", "DEVELOPER"))

            task_nodes = self._llm_mapper.from_llm_text(
                payload.get("result", {}).get("proposal", "")
            )

            await self._process.execute(
                plan_id=plan_id,
                story_id=story_id,
                role=role,
                task_nodes=task_nodes,
            )
            await msg.ack()
        except ValueError as exc:
            await self._publish_failure_from_consumer(payload or {}, str(exc))
            await msg.ack()
        except Exception as exc:
            if deliveries >= self._max_deliveries:
                logger.error(
                    "Max deliveries exceeded for derivation result: %s", exc
                )
                await msg.ack()
            else:
                logger.warning(
                    "Error processing derivation result (delivery %s): %s",
                    deliveries,
                    exc,
                )
                await msg.nak()

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

