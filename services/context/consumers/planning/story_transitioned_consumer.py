"""Consumer for planning.story.transitioned events."""

import asyncio
import json
import logging

from core.context.application.usecases.handle_story_phase_transition import (
    HandleStoryPhaseTransitionUseCase,
)
from core.context.infrastructure.mappers.planning_event_mapper import PlanningEventMapper
from core.shared.events.infrastructure import parse_required_envelope

from services.context.consumers.planning.base_consumer import BasePlanningConsumer

logger = logging.getLogger(__name__)


class StoryTransitionedConsumer(BasePlanningConsumer):
    """Inbound Adapter for planning.story.transitioned events (ACL).

    Following Hexagonal Architecture + DDD.
    """

    def __init__(self, js, use_case: HandleStoryPhaseTransitionUseCase):
        super().__init__(js=js, graph_command=None, cache_service=None)
        self._use_case = use_case

    async def start(self) -> None:
        self._subscription = await self.js.pull_subscribe(
            subject="planning.story.transitioned",
            durable="context-planning-story-transitions",
            stream="PLANNING_EVENTS",
        )
        logger.info("✓ StoryTransitionedConsumer: subscription created (DURABLE)")

        self._polling_task = asyncio.create_task(
            self._poll_messages(self._subscription, self._handle_message)
        )

    async def _handle_message(self, msg) -> None:
        """Orchestration: JSON → DTO → Entity → UseCase."""
        try:
            # 1. Parse JSON payload
            data = json.loads(msg.data.decode())

            # 2. Require EventEnvelope (no legacy fallback)
            try:
                envelope = parse_required_envelope(data)
            except ValueError as e:
                logger.error(
                    f"Dropping story.transitioned without valid EventEnvelope: {e}",
                    exc_info=True,
                )
                await msg.ack()
                return

            payload = envelope.payload

            logger.debug(
                f"📥 [EventEnvelope] Received story transitioned. "
                f"correlation_id={envelope.correlation_id}, "
                f"idempotency_key={envelope.idempotency_key[:16]}..., "
                f"event_type={envelope.event_type}"
            )

            # 2. JSON → Entity (via unified mapper - ACL)
            transition = PlanningEventMapper.payload_to_phase_transition(payload)

            # 3. Call use case
            await self._use_case.execute(transition)

            # 4. ACK
            await msg.ack()

        except (KeyError, ValueError) as e:
            logger.warning(f"Invalid event data: {e}", exc_info=True)
            await msg.nak()
        except Exception as e:
            logger.error(f"Error processing event: {e}", exc_info=True)
            await msg.nak()

