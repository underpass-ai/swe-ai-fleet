"""NATS messaging adapter for Planning Service."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from nats.aio.client import Client as NATS
from nats.js import JetStreamContext

from planning.application.ports import MessagingPort
from planning.domain import Comment, DecisionId, Reason, StoryId, StoryState, Title, UserName
from planning.infrastructure.mappers.event_payload_mapper import EventPayloadMapper

logger = logging.getLogger(__name__)


class NATSMessagingAdapter(MessagingPort):
    """
    Adapter for publishing domain events to NATS JetStream.

    Events Published:
    - story.created → Subject: planning.story.created
    - story.transitioned → Subject: planning.story.transitioned
    - decision.approved → Subject: planning.decision.approved
    - decision.rejected → Subject: planning.decision.rejected

    Stream: planning-events (persistent, file storage)
    """

    def __init__(self, nats_client: NATS, jetstream: JetStreamContext):
        """
        Initialize NATS messaging adapter.

        Args:
            nats_client: Connected NATS client.
            jetstream: JetStream context.
        """
        self.nc = nats_client
        self.js = jetstream
        logger.info("NATS messaging adapter initialized")

    async def publish_event(
        self,
        subject: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Publish a domain event to NATS.

        Args:
            subject: NATS subject (e.g., "planning.story.created").
            payload: Event payload (must be JSON-serializable).

        Raises:
            Exception: If publishing fails.
        """
        try:
            message = json.dumps(payload).encode("utf-8")
            ack = await self.js.publish(subject, message)
            logger.info(
                f"Event published: subject={subject}, "
                f"seq={ack.seq}, stream={ack.stream}"
            )
        except Exception as e:
            logger.error(f"Failed to publish event to {subject}: {e}", exc_info=True)
            raise

    async def publish_story_created(
        self,
        story_id: StoryId,
        title: Title,
        created_by: UserName,
    ) -> None:
        """
        Publish story.created event.

        Event consumers:
        - Orchestrator: May trigger automatic planning
        - Context Service: Record story in graph
        - Monitoring: Track story creation metrics

        Args:
            story_id: ID of created story.
            title: Story title.
            created_by: User who created the story.

        Raises:
            Exception: If publishing fails.
        """
        payload = EventPayloadMapper.story_created_payload(
            story_id=story_id,
            title=title,
            created_by=created_by,
        )

        await self.publish_event("planning.story.created", payload)

    async def publish_story_transitioned(
        self,
        story_id: StoryId,
        from_state: StoryState,
        to_state: StoryState,
        transitioned_by: UserName,
    ) -> None:
        """
        Publish story.transitioned event.

        Event consumers:
        - Orchestrator: Trigger actions on specific state changes
        - Context Service: Update context on phase transitions
        - Monitoring: Track FSM transitions

        Args:
            story_id: ID of story.
            from_state: Previous state.
            to_state: New state.
            transitioned_by: User who triggered transition.

        Raises:
            Exception: If publishing fails.
        """
        payload = EventPayloadMapper.story_transitioned_payload(
            story_id=story_id,
            from_state=from_state,
            to_state=to_state,
            transitioned_by=transitioned_by,
        )

        await self.publish_event("planning.story.transitioned", payload)

    async def publish_decision_approved(
        self,
        story_id: StoryId,
        decision_id: DecisionId,
        approved_by: UserName,
        comment: Comment | None = None,
    ) -> None:
        """
        Publish decision.approved event.

        Event consumers:
        - Orchestrator: Trigger execution of approved decision
        - Context Service: Record approval in graph
        - Monitoring: Track approval metrics

        Args:
            story_id: ID of story.
            decision_id: ID of decision.
            approved_by: User who approved.
            comment: Optional approval comment.

        Raises:
            Exception: If publishing fails.
        """
        payload = EventPayloadMapper.decision_approved_payload(
            story_id=story_id,
            decision_id=decision_id,
            approved_by=approved_by,
            comment=comment,
        )

        await self.publish_event("planning.decision.approved", payload)

    async def publish_decision_rejected(
        self,
        story_id: StoryId,
        decision_id: DecisionId,
        rejected_by: UserName,
        reason: Reason,
    ) -> None:
        """
        Publish decision.rejected event.

        Event consumers:
        - Orchestrator: Trigger re-deliberation
        - Context Service: Record rejection in graph
        - Monitoring: Track rejection metrics

        Args:
            story_id: ID of story.
            decision_id: ID of decision.
            rejected_by: User who rejected.
            reason: Rejection reason.

        Raises:
            Exception: If publishing fails.
        """
        payload = EventPayloadMapper.decision_rejected_payload(
            story_id=story_id,
            decision_id=decision_id,
            rejected_by=rejected_by,
            reason=reason,
        )

        await self.publish_event("planning.decision.rejected", payload)

    def _current_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.now(UTC).isoformat() + "Z"

