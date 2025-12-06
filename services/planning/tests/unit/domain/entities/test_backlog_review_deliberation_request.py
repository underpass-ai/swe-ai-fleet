"""Unit tests for BacklogReviewDeliberationRequest domain entity."""

import pytest
from planning.domain.entities.backlog_review_deliberation_request import (
    BacklogReviewDeliberationRequest,
)
from planning.domain.entities.backlog_review_task_description import (
    BacklogReviewTaskDescription,
)
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.task_constraints import (
    BacklogReviewTaskConstraints,
)
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)


class TestBacklogReviewDeliberationRequest:
    """Test suite for BacklogReviewDeliberationRequest."""

    @pytest.fixture
    def task_description_entity(self) -> BacklogReviewTaskDescription:
        """Fixture providing a valid task description entity."""
        return BacklogReviewTaskDescription.build_without_context(
            ceremony_id=BacklogReviewCeremonyId("BRC-123"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.ARCHITECT,
        )

    def test_build_for_role_architect(self, task_description_entity: BacklogReviewTaskDescription) -> None:
        """Test building request for ARCHITECT role."""
        request = BacklogReviewDeliberationRequest.build_for_role(
            task_description_entity=task_description_entity,
            role=BacklogReviewRole.ARCHITECT,
        )

        assert request.role == BacklogReviewRole.ARCHITECT
        assert request.task_description_entity == task_description_entity
        assert isinstance(request.constraints, BacklogReviewTaskConstraints)
        assert "technical feasibility" in request.constraints.rubric.lower()
        assert "Identify components needed" in request.constraints.requirements

    def test_build_for_role_qa(self, task_description_entity: BacklogReviewTaskDescription) -> None:
        """Test building request for QA role."""
        request = BacklogReviewDeliberationRequest.build_for_role(
            task_description_entity=task_description_entity,
            role=BacklogReviewRole.QA,
        )

        assert request.role == BacklogReviewRole.QA
        assert isinstance(request.constraints, BacklogReviewTaskConstraints)
        assert "testability" in request.constraints.rubric.lower()
        assert "test scenarios" in request.constraints.requirements[0]

    def test_build_for_role_devops(self, task_description_entity: BacklogReviewTaskDescription) -> None:
        """Test building request for DEVOPS role."""
        request = BacklogReviewDeliberationRequest.build_for_role(
            task_description_entity=task_description_entity,
            role=BacklogReviewRole.DEVOPS,
        )

        assert request.role == BacklogReviewRole.DEVOPS
        assert isinstance(request.constraints, BacklogReviewTaskConstraints)
        assert "infrastructure" in request.constraints.rubric.lower()
        assert "infrastructure components" in request.constraints.requirements[0]

    def test_rejects_invalid_role(self, task_description_entity: BacklogReviewTaskDescription) -> None:
        """Test that invalid role raises ValueError."""
        # Create invalid role by trying to use a string
        with pytest.raises(ValueError, match="role must be a BacklogReviewRole enum"):
            BacklogReviewDeliberationRequest(
                task_description_entity=task_description_entity,
                role="INVALID_ROLE",  # type: ignore
                constraints=BacklogReviewTaskConstraints(
                    rubric="Test rubric",
                    requirements=(),
                ),
            )

    def test_rejects_invalid_task_description_type(self) -> None:
        """Test that invalid task_description_entity type raises ValueError."""
        with pytest.raises(ValueError, match="task_description_entity must be a BacklogReviewTaskDescription"):
            BacklogReviewDeliberationRequest(
                task_description_entity="not an entity",  # type: ignore
                role=BacklogReviewRole.ARCHITECT,
                constraints=BacklogReviewTaskConstraints(
                    rubric="Test rubric",
                    requirements=(),
                ),
            )

    def test_rejects_invalid_constraints_type(self, task_description_entity: BacklogReviewTaskDescription) -> None:
        """Test that invalid constraints type raises ValueError."""
        with pytest.raises(ValueError, match="constraints must be a BacklogReviewTaskConstraints"):
            BacklogReviewDeliberationRequest(
                task_description_entity=task_description_entity,
                role=BacklogReviewRole.ARCHITECT,
                constraints="not constraints",  # type: ignore
            )

    def test_is_immutable(self, task_description_entity: BacklogReviewTaskDescription) -> None:
        """Test that entity is immutable (frozen)."""
        request = BacklogReviewDeliberationRequest.build_for_role(
            task_description_entity=task_description_entity,
            role=BacklogReviewRole.ARCHITECT,
        )

        # Attempting to modify should raise FrozenInstanceError
        with pytest.raises(Exception):  # FrozenInstanceError
            request.role = BacklogReviewRole.QA  # type: ignore

    def test_architect_constraints_content(self, task_description_entity: BacklogReviewTaskDescription) -> None:
        """Test that ARCHITECT constraints have correct content."""
        request = BacklogReviewDeliberationRequest.build_for_role(
            task_description_entity=task_description_entity,
            role=BacklogReviewRole.ARCHITECT,
        )

        constraints = request.constraints
        assert constraints.timeout_seconds == 180
        assert len(constraints.requirements) == 3
        assert "components" in constraints.requirements[0].lower()
        assert "tasks" in constraints.requirements[1].lower()
        assert "complexity" in constraints.requirements[2].lower()

    def test_qa_constraints_content(self, task_description_entity: BacklogReviewTaskDescription) -> None:
        """Test that QA constraints have correct content."""
        request = BacklogReviewDeliberationRequest.build_for_role(
            task_description_entity=task_description_entity,
            role=BacklogReviewRole.QA,
        )

        constraints = request.constraints
        assert constraints.timeout_seconds == 180
        assert len(constraints.requirements) == 3
        assert "test" in constraints.requirements[0].lower()
        assert "acceptance" in constraints.requirements[1].lower()
        assert "testing" in constraints.requirements[2].lower()

    def test_devops_constraints_content(self, task_description_entity: BacklogReviewTaskDescription) -> None:
        """Test that DEVOPS constraints have correct content."""
        request = BacklogReviewDeliberationRequest.build_for_role(
            task_description_entity=task_description_entity,
            role=BacklogReviewRole.DEVOPS,
        )

        constraints = request.constraints
        assert constraints.timeout_seconds == 180
        assert len(constraints.requirements) == 3
        assert "infrastructure" in constraints.requirements[0].lower()
        assert "deployment" in constraints.requirements[1].lower()
        assert "operational" in constraints.requirements[2].lower()

    def test_build_for_all_roles(self, task_description_entity: BacklogReviewTaskDescription) -> None:
        """Test building request for all valid roles."""
        roles = [
            BacklogReviewRole.ARCHITECT,
            BacklogReviewRole.QA,
            BacklogReviewRole.DEVOPS,
        ]

        for role in roles:
            request = BacklogReviewDeliberationRequest.build_for_role(
                task_description_entity=task_description_entity,
                role=role,
            )
            assert request.role == role
            assert isinstance(request.constraints, BacklogReviewTaskConstraints)
