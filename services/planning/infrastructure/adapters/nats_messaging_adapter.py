"""NATS messaging adapter for Planning Service."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from nats.aio.client import Client as NATS
from nats.js import JetStreamContext

from planning.application.ports import MessagingPort
from planning.domain import Comment, DecisionId, Reason, StoryId, StoryState, Title, UserName
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.infrastructure.mappers.event_payload_mapper import EventPayloadMapper
from planning.infrastructure.mappers.story_event_mapper import StoryEventMapper

logger = logging.getLogger(__name__)


class NATSMessagingAdapter(MessagingPort):
    """
    Adapter for publishing domain events to NATS JetStream.

    Events Published:
    - story.created → Subject: planning.story.created
    - story.transitioned → Subject: planning.story.transitioned
    - story.tasks_not_ready → Subject: planning.story.tasks_not_ready
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

    async def publish_story_tasks_not_ready(
        self,
        story_id: StoryId,
        reason: str,
        task_ids_without_priority: tuple[TaskId, ...],
        total_tasks: int,
    ) -> None:
        """
        Publish story.tasks_not_ready event.

        Event consumers:
        - PO UI: Notify Product Owner (HUMAN) that story needs reformulation
          This implements HUMAN-IN-THE-LOOP pattern - PO receives notification in UI
          and can intervene to reformulate the story or fix tasks
        - Monitoring: Track stories blocked by missing priorities
        - Orchestrator: May trigger re-derivation of tasks (after PO approval)

        Business Rule (Human-in-the-Loop):
        - PO (Product Owner) is HUMAN in swe-ai-fleet
        - This is a human gate: PO must approve/fix before story can proceed
        - PO receives notification in UI and decides whether to reformulate story
        - PO can fix tasks or reformulate story based on the notification
        - After PO intervention, story can retry transition to READY_FOR_EXECUTION

        Args:
            story_id: ID of story.
            reason: Reason why tasks are not ready.
            task_ids_without_priority: Tuple of TaskId VOs without priority.
            total_tasks: Total number of tasks for the story.

        Raises:
            Exception: If publishing fails.
        """
        from planning.domain.events.story_tasks_not_ready_event import StoryTasksNotReadyEvent

        # Create domain event
        event = StoryTasksNotReadyEvent(
            story_id=story_id,
            reason=reason,
            task_ids_without_priority=task_ids_without_priority,
            total_tasks=total_tasks,
            occurred_at=datetime.now(UTC),
        )

        # Convert to payload using mapper
        payload = StoryEventMapper.tasks_not_ready_event_to_payload(event)

        await self.publish_event("planning.story.tasks_not_ready", payload)

        logger.info(
            f"StoryTasksNotReadyEvent published: story_id={story_id}, "
            f"tasks_without_priority={len(task_ids_without_priority)}, "
            f"total_tasks={total_tasks}"
        )

    def _current_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.now(UTC).isoformat() + "Z"

