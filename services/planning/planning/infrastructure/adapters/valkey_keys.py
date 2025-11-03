"""Valkey (Redis) key schema for Planning Service."""

from planning.domain import StoryId, StoryState


class ValkeyKeys:
    """
    Static class: Centralized Valkey key schema.

    Infrastructure Responsibility:
    - Define all Redis key patterns in one place
    - Prevent typos and inconsistencies
    - Document the data model in Valkey

    Key Patterns:
    - planning:story:{story_id} → Hash with story details
    - planning:story:{story_id}:state → String with FSM state
    - planning:stories:all → Set of all story IDs
    - planning:stories:state:{state} → Set of story IDs by state
    """

    # Namespace prefix
    NAMESPACE = "planning"

    @staticmethod
    def story_hash(story_id: StoryId) -> str:
        """
        Key for story details hash.

        Args:
            story_id: Story identifier.

        Returns:
            Redis key for story hash.
        """
        return f"{ValkeyKeys.NAMESPACE}:story:{story_id.value}"

    @staticmethod
    def story_state(story_id: StoryId) -> str:
        """
        Key for story FSM state (fast lookup).

        Args:
            story_id: Story identifier.

        Returns:
            Redis key for story state.
        """
        return f"{ValkeyKeys.NAMESPACE}:story:{story_id.value}:state"

    @staticmethod
    def all_stories() -> str:
        """
        Key for set containing all story IDs.

        Returns:
            Redis key for all stories set.
        """
        return f"{ValkeyKeys.NAMESPACE}:stories:all"

    @staticmethod
    def stories_by_state(state: StoryState) -> str:
        """
        Key for set containing story IDs by state.

        Args:
            state: Story state to filter by.

        Returns:
            Redis key for stories in given state.
        """
        return f"{ValkeyKeys.NAMESPACE}:stories:state:{state.to_string()}"

