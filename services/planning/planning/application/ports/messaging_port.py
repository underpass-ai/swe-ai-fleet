"""Messaging port for Publishing domain events."""

from typing import Any, Protocol

from planning.domain import (
    Comment,
    DecisionId,
    Reason,
    StoryId,
    StoryState,
    TaskId,
    Title,
    UserName,
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

