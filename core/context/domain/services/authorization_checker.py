"""AuthorizationChecker - Domain service for authorization logic (RBAC L2)."""

from dataclasses import dataclass

from core.context.domain.role import Role
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.value_objects.role_visibility_policy import (
    RoleVisibilityPolicy,
    EntityVisibilityRule,
    VisibilityScope,
)
from core.context.domain.value_objects.authorization_result import AuthorizationResult
from core.context.ports.story_authorization_port import StoryAuthorizationPort


@dataclass
class AuthorizationChecker:
    """Domain service for checking authorization based on visibility rules.

    Encapsulates the business logic for determining if a user is authorized
    to access a specific story based on visibility policy.

    Pure domain logic that delegates to port for data queries.
    """

    story_auth_port: StoryAuthorizationPort

    async def check_story_access(
        self,
        story_id: StoryId,
        user_id: str,
        rule: EntityVisibilityRule,
    ) -> AuthorizationResult:
        """Check if user can access story based on visibility rule.

        Args:
            story_id: Story to check access for
            user_id: User requesting access
            rule: Visibility rule for stories

        Returns:
            AuthorizationResult (Value Object, NOT tuple)
        """
        # Full access - allow immediately
        if rule.allows_all_access():
            return AuthorizationResult.granted()

        # No access - deny immediately
        if rule.denies_all_access():
            return AuthorizationResult.denied("Role has no story access")

        # Scoped access - delegate to specific checker
        scope = rule.scope

        if scope == VisibilityScope.ASSIGNED:
            return await self._check_assigned_access(story_id, user_id)

        elif scope == VisibilityScope.EPIC_CHILDREN:
            return await self._check_epic_children_access(story_id, user_id)

        elif scope == VisibilityScope.TESTING_PHASE:
            return await self._check_testing_phase_access(story_id)

        elif scope == VisibilityScope.STORY_SCOPED:
            return await self._check_story_scoped_access(story_id, user_id)

        else:
            # Unknown scope - fail-fast
            return AuthorizationResult.denied(f"Unknown visibility scope: {scope.value}")

    async def _check_assigned_access(
        self,
        story_id: StoryId,
        user_id: str,
    ) -> AuthorizationResult:
        """Check ASSIGNED scope: Is story assigned to user?"""
        is_assigned = await self.story_auth_port.is_story_assigned_to_user(
            story_id,
            user_id,
        )

        if is_assigned:
            return AuthorizationResult.granted()

        return AuthorizationResult.denied(
            f"Story {story_id.to_string()} is not assigned to user {user_id}"
        )

    async def _check_epic_children_access(
        self,
        story_id: StoryId,
        user_id: str,
    ) -> AuthorizationResult:
        """Check EPIC_CHILDREN scope: Is story's epic assigned to user?"""
        # Get epic for this story (domain invariant: every story has epic)
        epic_id = await self.story_auth_port.get_epic_for_story(story_id)

        # Check if epic is assigned to user
        is_epic_assigned = await self.story_auth_port.is_epic_assigned_to_user(
            epic_id,
            user_id,
        )

        if is_epic_assigned:
            return AuthorizationResult.granted()

        return AuthorizationResult.denied(
            f"Story's epic {epic_id.to_string()} is not assigned to user {user_id}"
        )

    async def _check_testing_phase_access(
        self,
        story_id: StoryId,
    ) -> AuthorizationResult:
        """Check TESTING_PHASE scope: Is story in testing?"""
        is_testing = await self.story_auth_port.is_story_in_testing_phase(story_id)

        if is_testing:
            return AuthorizationResult.granted()

        return AuthorizationResult.denied(
            f"Story {story_id.to_string()} is not in testing phase"
        )

    async def _check_story_scoped_access(
        self,
        story_id: StoryId,
        user_id: str,
    ) -> AuthorizationResult:
        """Check STORY_SCOPED scope: Generic story-level access."""
        # For now, same as ASSIGNED
        # Can be extended for more complex rules
        return await self._check_assigned_access(story_id, user_id)

