"""Transition Story use case."""

from dataclasses import dataclass
from datetime import UTC, datetime

from planning.application.ports import MessagingPort, StoragePort
from planning.domain import Story, StoryId, StoryState, UserName
from planning.domain.value_objects.statuses.story_state import StoryStateEnum


class StoryNotFoundError(Exception):
    """Raised when story is not found."""
    pass


class InvalidTransitionError(Exception):
    """Raised when state transition is invalid."""
    pass


class TasksNotReadyError(Exception):
    """Raised when story cannot transition because tasks are not ready."""
    pass


@dataclass
class TransitionStoryUseCase:
    """
    Use Case: Transition story to a new state.

    Business Rules:
    - Transition must follow FSM rules
    - Story must exist
    - State changes are published as events

    Dependencies:
    - StoragePort: Retrieve and update story
    - MessagingPort: Publish story.transitioned event
    """

    storage: StoragePort
    messaging: MessagingPort

    async def execute(
        self,
        story_id: StoryId,
        target_state: StoryState,
        transitioned_by: UserName,
    ) -> Story:
        """
        Transition story to target state.

        Args:
            story_id: Domain StoryId value object.
            target_state: Target StoryState value object.
            transitioned_by: Domain UserName value object.

        Returns:
            Updated story instance.

        Raises:
            StoryNotFoundError: If story doesn't exist.
            InvalidTransitionError: If transition is invalid.
            StorageError: If update fails.
            MessagingError: If event publishing fails.
        """
        # Validation already done by Value Objects' __post_init__

        # Retrieve current story
        story = await self.storage.get_story(story_id)
        if story is None:
            raise StoryNotFoundError(f"Story not found: {story_id}")

        # Validate transition
        if not story.state.can_transition_to(target_state):
            raise InvalidTransitionError(
                f"Invalid transition: {story.state} → {target_state} "
                f"for story {story_id}"
            )

        # Business Rule: Story cannot be READY_FOR_EXECUTION if not all tasks have priorities defined
        # Priority must be >= 1 (valid priority from LLM), not default 1 (which means not set)
        # HUMAN-IN-THE-LOOP: If tasks are not ready, notify PO (HUMAN) via event
        # This is a human gate - PO receives notification in UI and can reformulate story
        # After PO intervention, story can retry transition to READY_FOR_EXECUTION
        if target_state.value == StoryStateEnum.READY_FOR_EXECUTION:
            tasks = await self.storage.list_tasks(story_id=story_id, limit=1000, offset=0)
            if not tasks:
                # Notify PO that story has no tasks
                await self.messaging.publish_story_tasks_not_ready(
                    story_id=story_id,
                    reason="No tasks defined. Story must have at least one task before being ready for development.",
                    task_ids_without_priority=(),
                    total_tasks=0,
                )
                raise TasksNotReadyError(
                    f"Story {story_id} cannot transition to READY_FOR_EXECUTION: "
                    f"No tasks defined. Story must have at least one task before being ready for development."
                )
            # Check for tasks with invalid priority (priority < 1 means not properly set by LLM)
            tasks_without_priority = [t for t in tasks if t.priority < 1]
            if tasks_without_priority:
                task_ids = tuple(t.task_id for t in tasks_without_priority)
                reason = (
                    f"{len(tasks_without_priority)} tasks without priority defined: "
                    f"{', '.join(str(tid) for tid in task_ids)}. "
                    f"All tasks must have priorities (>= 1) defined by LLM before story can be ready for development."
                )
                # Notify PO that story has tasks without priorities (PO can reformulate story)
                await self.messaging.publish_story_tasks_not_ready(
                    story_id=story_id,
                    reason=reason,
                    task_ids_without_priority=task_ids,
                    total_tasks=len(tasks),
                )
                raise TasksNotReadyError(
                    f"Story {story_id} cannot transition to READY_FOR_EXECUTION: {reason}"
                )

        # Transition to new state
        previous_state = story.state
        updated_story = story.transition_to(
            target_state=target_state,
            updated_at=datetime.now(UTC),
        )

        # Persist updated story
        await self.storage.update_story(updated_story)

        # Publish domain event
        await self.messaging.publish_story_transitioned(
            story_id=story_id,  # Pass Value Object directly
            from_state=previous_state,  # Pass Value Object directly
            to_state=target_state,  # Pass Value Object directly
            transitioned_by=transitioned_by,
        )

        return updated_story

