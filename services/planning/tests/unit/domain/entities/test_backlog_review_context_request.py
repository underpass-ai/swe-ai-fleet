"""Unit tests for BacklogReviewContextRequest domain entity."""

import pytest
from planning.domain.entities.backlog_review_context_request import (
    BacklogReviewContextRequest,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_phase import (
    BacklogReviewPhase,
)
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)
from planning.domain.value_objects.statuses.token_budget import TokenBudget


class TestBacklogReviewContextRequest:
    """Test suite for BacklogReviewContextRequest."""

    def test_create_valid_request(self) -> None:
        """Test creating a valid context request."""
        story_id = StoryId("ST-123")
        request = BacklogReviewContextRequest(
            story_id=story_id,
            role=BacklogReviewRole.ARCHITECT,
            phase=BacklogReviewPhase.DESIGN,
            token_budget=TokenBudget.STANDARD,
        )

        assert request.story_id == story_id
        assert request.role == BacklogReviewRole.ARCHITECT
        assert request.phase == BacklogReviewPhase.DESIGN
        assert request.token_budget == TokenBudget.STANDARD
        assert request.token_budget.value == 2000

    def test_build_for_design_phase(self) -> None:
        """Test builder method for DESIGN phase."""
        story_id = StoryId("ST-123")
        request = BacklogReviewContextRequest.build_for_design_phase(
            story_id=story_id,
            role=BacklogReviewRole.ARCHITECT,
            token_budget=TokenBudget.STANDARD,
        )

        assert request.story_id == story_id
        assert request.role == BacklogReviewRole.ARCHITECT
        assert request.phase == BacklogReviewPhase.DESIGN
        assert request.token_budget == TokenBudget.STANDARD

    def test_build_for_design_phase_default_token_budget(self) -> None:
        """Test builder method with default token budget."""
        story_id = StoryId("ST-123")
        request = BacklogReviewContextRequest.build_for_design_phase(
            story_id=story_id,
            role=BacklogReviewRole.QA,
        )

        assert request.phase == BacklogReviewPhase.DESIGN
        assert request.token_budget == TokenBudget.STANDARD  # Default value
        assert request.token_budget.value == 2000

    def test_create_with_default_token_budget(self) -> None:
        """Test creating request with default token budget."""
        story_id = StoryId("ST-123")
        request = BacklogReviewContextRequest(
            story_id=story_id,
            role=BacklogReviewRole.QA,
            phase=BacklogReviewPhase.DESIGN,
        )

        assert request.token_budget == TokenBudget.STANDARD  # Default value
        assert request.token_budget.value == 2000

    def test_create_with_all_valid_roles(self) -> None:
        """Test creating request with all valid roles."""
        story_id = StoryId("ST-123")
        valid_roles = [
            BacklogReviewRole.ARCHITECT,
            BacklogReviewRole.QA,
            BacklogReviewRole.DEVOPS,
        ]

        for role in valid_roles:
            request = BacklogReviewContextRequest(
                story_id=story_id,
                role=role,
                phase=BacklogReviewPhase.DESIGN,
            )
            assert request.role == role

    def test_create_with_all_valid_phases(self) -> None:
        """Test creating request with all valid phases."""
        story_id = StoryId("ST-123")
        valid_phases = [
            BacklogReviewPhase.DESIGN,
            BacklogReviewPhase.BUILD,
            BacklogReviewPhase.TEST,
            BacklogReviewPhase.DOCS,
        ]

        for phase in valid_phases:
            request = BacklogReviewContextRequest(
                story_id=story_id,
                role=BacklogReviewRole.ARCHITECT,
                phase=phase,
            )
            assert request.phase == phase

    def test_rejects_empty_story_id(self) -> None:
        """Test that empty story_id raises ValueError."""
        # StoryId itself will reject empty string, but test entity validation
        with pytest.raises(ValueError, match="StoryId cannot be empty"):
            # This will fail at StoryId creation, not at BacklogReviewContextRequest
            StoryId("")

    def test_rejects_invalid_role_type(self) -> None:
        """Test that invalid role type raises ValueError."""
        with pytest.raises(ValueError, match="role must be a BacklogReviewRole enum"):
            BacklogReviewContextRequest(
                story_id=StoryId("ST-123"),
                role="ARCHITECT",  # String instead of enum
                phase=BacklogReviewPhase.DESIGN,
            )

    def test_rejects_invalid_phase_type(self) -> None:
        """Test that invalid phase type raises ValueError."""
        with pytest.raises(ValueError, match="phase must be a BacklogReviewPhase enum"):
            BacklogReviewContextRequest(
                story_id=StoryId("ST-123"),
                role=BacklogReviewRole.ARCHITECT,
                phase="DESIGN",  # String instead of enum
            )

    def test_rejects_invalid_token_budget_type(self) -> None:
        """Test that invalid token_budget type raises ValueError."""
        with pytest.raises(ValueError, match="token_budget must be a TokenBudget enum"):
            BacklogReviewContextRequest(
                story_id=StoryId("ST-123"),
                role=BacklogReviewRole.ARCHITECT,
                phase=BacklogReviewPhase.DESIGN,
                token_budget=2000,  # int instead of enum
            )

    def test_to_context_port_params(self) -> None:
        """Test conversion to ContextPort parameters."""
        story_id = StoryId("ST-123")
        request = BacklogReviewContextRequest(
            story_id=story_id,
            role=BacklogReviewRole.ARCHITECT,
            phase=BacklogReviewPhase.DESIGN,
            token_budget=TokenBudget.LARGE,
        )

        params = request.to_context_port_params()

        assert params["story_id"] == "ST-123"
        assert params["role"] == "ARCHITECT"
        assert params["phase"] == "DESIGN"
        assert params["token_budget"] == 4000  # TokenBudget.LARGE.value

    def test_is_immutable(self) -> None:
        """Test that entity is immutable (frozen)."""
        story_id = StoryId("ST-123")
        request = BacklogReviewContextRequest(
            story_id=story_id,
            role=BacklogReviewRole.ARCHITECT,
            phase=BacklogReviewPhase.DESIGN,
        )

        # Attempting to modify should raise FrozenInstanceError
        with pytest.raises(Exception):  # FrozenInstanceError
            request.role = BacklogReviewRole.QA  # type: ignore

    def test_build_for_design_phase_all_roles(self) -> None:
        """Test builder method works for all roles."""
        story_id = StoryId("ST-123")
        roles = [
            BacklogReviewRole.ARCHITECT,
            BacklogReviewRole.QA,
            BacklogReviewRole.DEVOPS,
        ]

        for role in roles:
            request = BacklogReviewContextRequest.build_for_design_phase(
                story_id=story_id,
                role=role,
            )
            assert request.role == role
            assert request.phase == BacklogReviewPhase.DESIGN
            assert request.token_budget == TokenBudget.STANDARD

    def test_create_with_all_token_budgets(self) -> None:
        """Test creating request with all token budget values."""
        story_id = StoryId("ST-123")
        budgets = [
            TokenBudget.SMALL,
            TokenBudget.STANDARD,
            TokenBudget.LARGE,
        ]

        for budget in budgets:
            request = BacklogReviewContextRequest(
                story_id=story_id,
                role=BacklogReviewRole.ARCHITECT,
                phase=BacklogReviewPhase.DESIGN,
                token_budget=budget,
            )
            assert request.token_budget == budget

    def test_build_for_design_phase_with_custom_token_budget(self) -> None:
        """Test builder method with custom token budget."""
        story_id = StoryId("ST-123")
        request = BacklogReviewContextRequest.build_for_design_phase(
            story_id=story_id,
            role=BacklogReviewRole.ARCHITECT,
            token_budget=TokenBudget.LARGE,
        )

        assert request.phase == BacklogReviewPhase.DESIGN
        assert request.token_budget == TokenBudget.LARGE
        assert request.token_budget.value == 4000

    def test_to_context_port_params_converts_enums_to_primitives(self) -> None:
        """Test that to_context_port_params converts enums to primitives."""
        story_id = StoryId("ST-123")
        request = BacklogReviewContextRequest(
            story_id=story_id,
            role=BacklogReviewRole.DEVOPS,
            phase=BacklogReviewPhase.BUILD,
            token_budget=TokenBudget.SMALL,
        )

        params = request.to_context_port_params()

        # Verify all values are primitives (not enums)
        assert isinstance(params["story_id"], str)
        assert isinstance(params["role"], str)
        assert isinstance(params["phase"], str)
        assert isinstance(params["token_budget"], int)

        # Verify correct values
        assert params["story_id"] == "ST-123"
        assert params["role"] == "DEVOPS"
        assert params["phase"] == "BUILD"
        assert params["token_budget"] == 1000
