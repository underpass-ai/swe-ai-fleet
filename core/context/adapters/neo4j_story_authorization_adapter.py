"""Neo4jStoryAuthorizationAdapter - Neo4j implementation of StoryAuthorizationPort."""

from core.context.adapters.neo4j_query_store import Neo4jQueryStore
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.neo4j_queries import Neo4jQuery
from core.context.ports.story_authorization_port import StoryAuthorizationPort


class Neo4jStoryAuthorizationAdapter(StoryAuthorizationPort):
    """Neo4j adapter for story authorization checks.

    Implements RBAC L2 authorization queries using role-filtered Neo4j queries.

    Defense in depth: Performs authorization checks at the database level.
    """

    def __init__(self, store: Neo4jQueryStore) -> None:
        """Initialize adapter with Neo4j query store.

        Args:
            store: Neo4j query execution store
        """
        self._store = store

    async def is_story_assigned_to_user(
        self,
        story_id: StoryId,
        user_id: str,
    ) -> bool:
        """Check if story is assigned to user.

        Args:
            story_id: Story to check
            user_id: User ID

        Returns:
            True if story is assigned to user
        """
        results = self._store.query(
            Neo4jQuery.CHECK_STORY_ASSIGNED_TO_USER.value,
            {
                "story_id": story_id.to_string(),
                "user_id": user_id,
            },
        )

        if not results:
            return False

        return bool(results[0].get("is_assigned", False))

    async def get_epic_for_story(self, story_id: StoryId) -> EpicId:
        """Get epic that contains this story.

        Args:
            story_id: Story identifier

        Returns:
            Epic ID

        Raises:
            ValueError: If epic not found (domain invariant violation)
        """
        results = self._store.query(
            Neo4jQuery.GET_EPIC_BY_STORY.value,
            {"story_id": story_id.to_string()},
        )

        if not results:
            raise ValueError(
                f"Epic not found for story {story_id.to_string()}. "
                f"Domain invariant violation: Every story must have an epic."
            )

        epic_id_str = results[0].get("epic_id")
        if not epic_id_str:
            raise ValueError(
                f"Epic ID is null for story {story_id.to_string()}. "
                f"Database integrity error."
            )

        return EpicId(value=str(epic_id_str))

    async def is_epic_assigned_to_user(
        self,
        epic_id: EpicId,
        user_id: str,
    ) -> bool:
        """Check if epic is assigned to user.

        Args:
            epic_id: Epic to check
            user_id: User ID

        Returns:
            True if epic is assigned to user
        """
        results = self._store.query(
            Neo4jQuery.CHECK_EPIC_ASSIGNED_TO_USER.value,
            {
                "epic_id": epic_id.to_string(),
                "user_id": user_id,
            },
        )

        if not results:
            return False

        return bool(results[0].get("is_assigned", False))

    async def is_story_in_testing_phase(self, story_id: StoryId) -> bool:
        """Check if story is in testing phase.

        Args:
            story_id: Story to check

        Returns:
            True if story is in testing phase
        """
        results = self._store.query(
            Neo4jQuery.CHECK_STORY_IN_TESTING.value,
            {"story_id": story_id.to_string()},
        )

        if not results:
            return False

        return bool(results[0].get("in_testing", False))

