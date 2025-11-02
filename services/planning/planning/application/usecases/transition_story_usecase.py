"""Transition Story use case."""

from dataclasses import dataclass
from datetime import UTC, datetime

from planning.application.ports import MessagingPort, StoragePort
from planning.domain import Story, StoryId, StoryState, UserName


class StoryNotFoundError(Exception):
    """Raised when story is not found."""
    pass


class InvalidTransitionError(Exception):
    """Raised when state transition is invalid."""
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

