"""Simplified unit tests for RbacContextApplicationService."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from core.context.application.rbac_context_service import RbacContextApplicationService
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.get_role_based_context_request import GetRoleBasedContextRequest
from core.context.domain.role import Role
from core.context.domain.value_objects.authorization_result import AuthorizationResult
from core.context.domain.value_objects.role_visibility_policy import (
    EntityVisibilityRule,
    RoleVisibilityPolicy,
    VisibilityScope,
)


class TestRbacContextApplicationServiceSimple:
    """Simplified test suite for RbacContextApplicationService."""
    
    @pytest.fixture
    def visibility_policies(self) -> dict[Role, RoleVisibilityPolicy]:
        """Create test visibility policies."""
        return {
            Role.DEVELOPER: RoleVisibilityPolicy(
                role=Role.DEVELOPER,
                epic_rule=EntityVisibilityRule(VisibilityScope.ALL, None, {}),
                story_rule=EntityVisibilityRule(VisibilityScope.ASSIGNED, "assigned_to", {}),
                task_rule=EntityVisibilityRule(VisibilityScope.ASSIGNED, "role", {}),
                decision_rule=EntityVisibilityRule(VisibilityScope.ALL, None, {}),
                plan_rule=EntityVisibilityRule(VisibilityScope.ALL, None, {}),
                milestone_rule=EntityVisibilityRule(VisibilityScope.ALL, None, {}),
                summary_rule=EntityVisibilityRule(VisibilityScope.ALL, None, {}),
            ),
        }
    
    @pytest.mark.asyncio
    async def test_authorization_checked_before_rehydration(
        self,
        visibility_policies: dict[Role, RoleVisibilityPolicy],
    ) -> None:
        """Test that authorization is checked before rehydration (RBAC L2)."""
        # Create service with mocks
        mock_rehydration = AsyncMock()
        mock_column_filter = MagicMock()
        mock_auth_checker = AsyncMock()
        mock_audit = AsyncMock()
        
        service = RbacContextApplicationService(
            rehydration_service=mock_rehydration,
            column_filter=mock_column_filter,
            authorization_checker=mock_auth_checker,
            audit_logger=mock_audit,
            visibility_policies=visibility_policies,
        )
        
        request = GetRoleBasedContextRequest(
            story_id=StoryId(value="story-123"),
            requesting_role=Role.DEVELOPER,
            user_id="user-456",
            include_timeline=False,
            include_summaries=False,
            timeline_events=10,
        )
        
        # Mock: Authorization DENIED
        mock_auth_checker.check_story_access.return_value = AuthorizationResult.denied(
            "Story not assigned"
        )
        
        # Should raise ValueError and NOT call rehydration
        with pytest.raises(ValueError, match="Access denied"):
            await service.get_filtered_context(request)
        
        # Rehydration should NOT be called (early return)
        mock_rehydration.rehydrate_session.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_fails_fast_when_no_policy_for_role(
        self,
        visibility_policies: dict[Role, RoleVisibilityPolicy],
    ) -> None:
        """Test fail-fast when no visibility policy exists for role."""
        service = RbacContextApplicationService(
            rehydration_service=AsyncMock(),
            column_filter=MagicMock(),
            authorization_checker=AsyncMock(),
            audit_logger=AsyncMock(),
            visibility_policies=visibility_policies,
        )
        
        request = GetRoleBasedContextRequest(
            story_id=StoryId(value="story-123"),
            requesting_role=Role.ARCHITECT,  # No policy in fixture
            user_id="user-456",
            include_timeline=False,
            include_summaries=False,
            timeline_events=10,
        )
        
        with pytest.raises(ValueError, match="No visibility policy defined"):
            await service.get_filtered_context(request)
    
    @pytest.mark.asyncio
    async def test_fails_fast_when_role_has_no_story_access(self) -> None:
        """Test fail-fast when role's story_rule is NONE."""
        # Policy with NO story access
        policies = {
            Role.DEVELOPER: RoleVisibilityPolicy(
                role=Role.DEVELOPER,
                epic_rule=EntityVisibilityRule(VisibilityScope.ALL, None, {}),
                story_rule=EntityVisibilityRule(VisibilityScope.NONE, None, {}),
                task_rule=EntityVisibilityRule(VisibilityScope.ALL, None, {}),
                decision_rule=EntityVisibilityRule(VisibilityScope.ALL, None, {}),
                plan_rule=EntityVisibilityRule(VisibilityScope.ALL, None, {}),
                milestone_rule=EntityVisibilityRule(VisibilityScope.ALL, None, {}),
                summary_rule=EntityVisibilityRule(VisibilityScope.ALL, None, {}),
            ),
        }
        
        service = RbacContextApplicationService(
            rehydration_service=AsyncMock(),
            column_filter=MagicMock(),
            authorization_checker=AsyncMock(),
            audit_logger=AsyncMock(),
            visibility_policies=policies,
        )
        
        request = GetRoleBasedContextRequest(
            story_id=StoryId(value="story-123"),
            requesting_role=Role.DEVELOPER,
            user_id="user-456",
            include_timeline=False,
            include_summaries=False,
            timeline_events=10,
        )
        
        with pytest.raises(ValueError, match="no story access"):
            await service.get_filtered_context(request)

