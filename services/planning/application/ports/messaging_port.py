"""Messaging port for Publishing domain events."""

from typing import Any, Protocol

from datetime import datetime

from planning.domain.value_objects.content.comment import Comment
from planning.domain.value_objects.identifiers.decision_id import DecisionId
from planning.domain.value_objects.content.reason import Reason
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.story_state import StoryState
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
)


class MessagingPort(Protocol):
    """
    Port (interface) for publishing domain events to NATS.

    Events Published:
    - story.created
    - story.transitioned
    - story.updated
    - decision.approved
    - decision.rejected
    """

    async def publish_event(
        self,
        subject: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Publish a domain event to NATS.

        Args:
            subject: NATS subject (e.g., "story.created").
            payload: Event payload (must be JSON-serializable).

        Raises:
            MessagingError: If publishing fails.
        """
        ...

    async def publish_story_created(
        self,
        story_id: StoryId,
        title: Title,
        created_by: UserName,
    ) -> None:
        """
        Publish story.created event.

        Args:
            story_id: Domain StoryId value object.
            title: Domain Title value object.
            created_by: Domain UserName value object.

        Raises:
            MessagingError: If publishing fails.
        """
        ...

    async def publish_story_transitioned(
        self,
        story_id: StoryId,
        from_state: StoryState,
        to_state: StoryState,
        transitioned_by: UserName,
    ) -> None:
        """
        Publish story.transitioned event.

        Args:
            story_id: Domain StoryId value object.
            from_state: Previous StoryState value object.
            to_state: New StoryState value object.
            transitioned_by: Domain UserName value object.

        Raises:
            MessagingError: If publishing fails.
        """
        ...

    async def publish_decision_approved(
        self,
        story_id: StoryId,
        decision_id: DecisionId,
        approved_by: UserName,
        comment: Comment | None = None,
    ) -> None:
        """
        Publish decision.approved event.

        Args:
            story_id: Domain StoryId value object.
            decision_id: Domain DecisionId value object.
            approved_by: Domain UserName value object.
            comment: Optional Comment value object.

        Raises:
            MessagingError: If publishing fails.
        """
        ...

    async def publish_decision_rejected(
        self,
        story_id: StoryId,
        decision_id: DecisionId,
        rejected_by: UserName,
        reason: Reason,
    ) -> None:
        """
        Publish decision.rejected event.

        Args:
            story_id: Domain StoryId value object.
            decision_id: Domain DecisionId value object.
            rejected_by: Domain UserName value object.
            reason: Domain Reason value object.

        Raises:
            MessagingError: If publishing fails.
        """
        ...

    async def publish_story_tasks_not_ready(
        self,
        story_id: StoryId,
        reason: str,
        task_ids_without_priority: tuple[TaskId, ...],
        total_tasks: int,
    ) -> None:
        """
        Publish story.tasks_not_ready event.

        This event notifies the Product Owner (HUMAN) that a story cannot transition to
        READY_FOR_EXECUTION because tasks are missing priorities.

        Business Rule:
        - PO (Product Owner) is HUMAN in swe-ai-fleet
        - PO receives notification in UI and can reformulate story if needed

        Args:
            story_id: Domain StoryId value object.
            reason: Reason why tasks are not ready.
            task_ids_without_priority: Tuple of TaskId VOs without priority.
            total_tasks: Total number of tasks for the story.

        Raises:
            MessagingError: If publishing fails.
        """
        ...

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

        This event notifies subscribers that a backlog review ceremony has started.

        Args:
            ceremony_id: Domain BacklogReviewCeremonyId value object.
            status: Domain BacklogReviewCeremonyStatus value object.
            total_stories: Total number of stories in the ceremony.
            deliberations_submitted: Number of deliberation requests submitted.
            started_by: Domain UserName value object.
            started_at: Datetime when ceremony was started.

        Raises:
            MessagingError: If publishing fails.
        """
        ...

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
            MessagingError: If publishing fails.
        """
        ...

