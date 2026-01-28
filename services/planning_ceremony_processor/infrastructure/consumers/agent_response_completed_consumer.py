"""Consumer for agent.response.completed (ceremony advancement).

Subscribes to agent.response.completed, parses envelope, and advances ceremony state
(load instance, run next step or transition). Advancement logic is TODO; skeleton logs.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from core.shared.events.infrastructure import parse_required_envelope
from nats.aio.client import Client
from nats.js import JetStreamContext

logger = logging.getLogger(__name__)

AGENT_RESPONSES_STREAM = "AGENT_RESPONSES"
AGENT_RESPONSE_COMPLETED_SUBJECT = "agent.response.completed"
DURABLE_NAME = "planning-ceremony-processor-agent-response-completed-v1"


class AgentResponseCompletedConsumer:
    """Consumes agent.response.completed to advance ceremony state.

    On message: parse EventEnvelope, extract correlation_id/task_id, then advance
    (load instance, run next step or transition). Advancement is TODO; logs for now.
    """

    def __init__(
        self,
        nats_client: Client,
        jetstream: JetStreamContext,
        max_deliveries: int = 3,
    ) -> None:
        self._nc = nats_client
        self._js = jetstream
        self._max_deliveries = max_deliveries
        self._subscription: Any = None
        self._polling_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start consuming agent.response.completed."""
        try:
            self._subscription = await self._js.pull_subscribe(
                subject=AGENT_RESPONSE_COMPLETED_SUBJECT,
                durable=DURABLE_NAME,
                stream=AGENT_RESPONSES_STREAM,
            )
            logger.info(
                "✓ AgentResponseCompletedConsumer: subscription created (durable=%s)",
                DURABLE_NAME,
            )
            self._polling_task = asyncio.create_task(self._poll_messages())
        except Exception as e:
            logger.error(
                "Failed to start AgentResponseCompletedConsumer: %s",
                e,
                exc_info=True,
            )
            raise

    async def stop(self) -> None:
        """Stop the consumer. Suppresses CancelledError so shutdown can continue."""
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                logger.info("✓ AgentResponseCompletedConsumer stopped")
        else:
            logger.info("✓ AgentResponseCompletedConsumer stopped")

    async def _poll_messages(self) -> None:
        """Poll for messages."""
        logger.info("🔄 AgentResponseCompletedConsumer: polling started")
        while True:
            try:
                msgs = await self._subscription.fetch(batch=1, timeout=5)
                for msg in msgs:
                    await self._handle_message(msg)
            except asyncio.CancelledError:
                raise
            except TimeoutError:
                continue
            except Exception as e:
                logger.error("Error polling agent.response.completed: %s", e, exc_info=True)
                await asyncio.sleep(5)

    async def _handle_message(self, msg: Any) -> None:
        """Handle agent.response.completed message."""
        try:
            deliveries = getattr(msg.metadata, "num_delivered", 1)
        except AttributeError:
            deliveries = 1

        try:
            data = json.loads(msg.data.decode("utf-8"))
            envelope = parse_required_envelope(data)
            correlation_id = envelope.correlation_id or ""
            payload = envelope.payload
            task_id = (payload or {}).get("task_id", "")

            logger.info(
                "📥 agent.response.completed: correlation_id=%s task_id=%s",
                correlation_id,
                task_id,
            )
            # TODO(4.4): Advance ceremony state — load instance by correlation_id/task_id,
            # run next step or apply transition, persist. Requires persistence_port and
            # step_handler_port; implement AdvanceCeremonyOnAgentCompletedUseCase.
            await msg.ack()
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in agent.response.completed: %s", e)
            if deliveries >= self._max_deliveries:
                await msg.ack()
            else:
                await msg.nak()
        except ValueError as e:
            logger.warning("Invalid envelope in agent.response.completed: %s", e)
            await msg.ack()
        except Exception as e:
            logger.error(
                "Error processing agent.response.completed (delivery %s): %s",
                deliveries,
                e,
                exc_info=True,
            )
            if deliveries >= self._max_deliveries:
                await msg.ack()
            else:
                await msg.nak()
