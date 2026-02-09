"""NATS messaging adapter for Planning Service."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from core.shared.events import EventEnvelope, create_event_envelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from nats.aio.client import Client as NATS
from nats.js import JetStreamContext
from planning.application.ports import MessagingPort
from planning.domain import Comment, DecisionId, Reason, StoryId, StoryState, Title, UserName
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.nats_subject import NATSSubject
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
)
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
        Publish a domain event to NATS with EventEnvelope.

        Args:
            subject: NATS subject (e.g., "planning.story.created").
            payload: Event payload (must be JSON-serializable).

        Raises:
            Exception: If publishing fails.
        """
        # Extract entity_id from payload for idempotency key
        # Try common fields: plan_id, ceremony_id, story_id, etc.
        entity_id = (
            payload.get("plan_id")
            or payload.get("ceremony_id")
            or payload.get("story_id")
            or payload.get("task_id")
            or payload.get("epic_id")
            or payload.get("project_id")
            or "unknown"
        )

        event_type = subject
        operation = payload.get("operation") or "publish"

        envelope = create_event_envelope(
            event_type=event_type,
            payload=payload,
            producer="planning-service",
            entity_id=str(entity_id),
            operation=operation,
        )

        await self._publish_envelope(subject, envelope)

    async def _publish_envelope(
        self,
        subject: str,
        envelope: EventEnvelope,
    ) -> None:
        """
        Publish an event with EventEnvelope to NATS JetStream.

        Args:
            subject: NATS subject
            envelope: Event envelope with idempotency_key, correlation_id, etc.

        Raises:
            Exception: If publishing fails
        """
        try:
            # Serialize envelope to JSON using infrastructure mapper
            message = json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8")

            # Publish to JetStream
            ack = await self.js.publish(subject, message)

            logger.info(
                f"✅ Published event to {subject}: "
                f"stream={ack.stream}, sequence={ack.seq}, "
                f"idempotency_key={envelope.idempotency_key[:16]}..., "
                f"correlation_id={envelope.correlation_id}"
            )

        except Exception as e:
            error_msg = f"Failed to publish event to {subject}: {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

    async def publish_story_created(
        self,
        story_id: StoryId,
        epic_id: EpicId,
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
            epic_id: Parent Epic ID (domain invariant).
            title: Story title.
            created_by: User who created the story.

        Raises:
            Exception: If publishing fails.
        """
        payload = EventPayloadMapper.story_created_payload(
            story_id=story_id,
            epic_id=epic_id,
            title=title,
            created_by=created_by,
        )

        # Create event envelope with idempotency key
        envelope = create_event_envelope(
            event_type="planning.story.created",
            payload=payload,
            producer="planning-service",
            entity_id=str(story_id),
            operation="create",
        )

        await self._publish_envelope(str(NATSSubject.STORY_CREATED), envelope)

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

        # Create event envelope with idempotency key
        envelope = create_event_envelope(
            event_type="planning.story.transitioned",
            payload=payload,
            producer="planning-service",
            entity_id=str(story_id),
            operation=f"transition_{from_state.value}_to_{to_state.value}",
        )

        await self._publish_envelope(str(NATSSubject.STORY_TRANSITIONED), envelope)

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

        # Create event envelope with idempotency key
        envelope = create_event_envelope(
            event_type="planning.decision.approved",
            payload=payload,
            producer="planning-service",
            entity_id=str(decision_id),
            operation="approve",
        )

        await self._publish_envelope(str(NATSSubject.DECISION_APPROVED), envelope)

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

        # Create event envelope with idempotency key
        envelope = create_event_envelope(
            event_type="planning.decision.rejected",
            payload=payload,
            producer="planning-service",
            entity_id=str(decision_id),
            operation="reject",
        )

        await self._publish_envelope(str(NATSSubject.DECISION_REJECTED), envelope)

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

        # Create event envelope with idempotency key
        envelope = create_event_envelope(
            event_type="planning.story.tasks_not_ready",
            payload=payload,
            producer="planning-service",
            entity_id=str(story_id),
            operation="tasks_not_ready",
        )

        await self._publish_envelope(str(NATSSubject.STORY_TASKS_NOT_READY), envelope)

        logger.info(
            f"StoryTasksNotReadyEvent published: story_id={story_id}, "
            f"tasks_without_priority={len(task_ids_without_priority)}, "
            f"total_tasks={total_tasks}, "
            f"idempotency_key={envelope.idempotency_key[:16]}..., "
            f"correlation_id={envelope.correlation_id}"
        )

    async def publish_ceremony_started(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        status: BacklogReviewCeremonyStatus,
        total_stories: int,
        deliberations_submitted: int,
        started_by: UserName,
        started_at: datetime,
    ) -> None:
        """
        Publish ceremony.started event.

        Event consumers:
        - UI: Update ceremony status display
        - Monitoring: Track ceremony start metrics

        Args:
            ceremony_id: ID of ceremony.
            status: Current ceremony status.
            total_stories: Total number of stories in the ceremony.
            deliberations_submitted: Number of deliberation requests submitted.
            started_by: User who started the ceremony.
            started_at: Datetime when ceremony was started.

        Raises:
            Exception: If publishing fails.
        """
        payload = EventPayloadMapper.ceremony_started_payload(
            ceremony_id=ceremony_id,
            status=status,
            total_stories=total_stories,
            deliberations_submitted=deliberations_submitted,
            started_by=started_by,
            started_at=started_at,
        )

        # Create event envelope with idempotency key
        envelope = create_event_envelope(
            event_type="planning.backlog_review.ceremony.started",
            payload=payload,
            producer="planning-service",
            entity_id=str(ceremony_id),
            operation="start",
        )

        await self._publish_envelope(str(NATSSubject.BACKLOG_REVIEW_CEREMONY_STARTED), envelope)

    async def publish_dualwrite_reconcile_requested(
        self,
        operation_id: str,
        operation_type: str,
        operation_data: dict[str, Any],
    ) -> None:
        """Publish dualwrite.reconcile.requested event.

        Published when Neo4j write fails after successful Valkey write.
        The reconciler will consume this event and retry the Neo4j operation.

        Args:
            operation_id: Unique identifier for the dual write operation
            operation_type: Type of operation (e.g., "save_story", "save_task")
            operation_data: Operation-specific data needed for reconciliation

        Raises:
            Exception: If publishing fails.
        """
        payload = {
            "operation_id": operation_id,
            "operation_type": operation_type,
            "operation_data": operation_data,
        }

        # Create event envelope with idempotency key
        envelope = create_event_envelope(
            event_type="planning.dualwrite.reconcile.requested",
            payload=payload,
            producer="planning-service",
            entity_id=operation_id,
            operation="reconcile",
        )

        await self._publish_envelope(
            str(NATSSubject.DUALWRITE_RECONCILE_REQUESTED),
            envelope,
        )

        logger.info(
            f"Published dualwrite reconcile event: operation_id={operation_id}, "
            f"operation_type={operation_type}"
        )

    def _current_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.now(UTC).isoformat() + "Z"
