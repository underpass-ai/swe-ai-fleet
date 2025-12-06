"""Unit tests for BacklogReviewDeliberationMapper."""

from planning.application.ports.orchestrator_port import (
    DeliberationRequest,
    TaskConstraints,
)
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
from planning.infrastructure.mappers.backlog_review_deliberation_mapper import (
    BacklogReviewDeliberationMapper,
)


class TestBacklogReviewDeliberationMapper:
    """Test suite for BacklogReviewDeliberationMapper."""

    def test_to_deliberation_request_architect(self) -> None:
        """Test conversion for ARCHITECT role."""
        task_description = BacklogReviewTaskDescription.build_without_context(
            ceremony_id=BacklogReviewCeremonyId("BRC-123"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.ARCHITECT,
        )

        entity = BacklogReviewDeliberationRequest.build_for_role(
            task_description_entity=task_description,
            role=BacklogReviewRole.ARCHITECT,
        )

        result = BacklogReviewDeliberationMapper.to_deliberation_request(entity)

        assert isinstance(result, DeliberationRequest)
        assert result.role == "ARCHITECT"
        assert result.rounds == 1
        assert result.num_agents == 3
        assert result.constraints is not None
        assert isinstance(result.constraints, TaskConstraints)
        assert "technical feasibility" in result.constraints.rubric.lower()

    def test_to_deliberation_request_qa(self) -> None:
        """Test conversion for QA role."""
        task_description = BacklogReviewTaskDescription.build_without_context(
            ceremony_id=BacklogReviewCeremonyId("BRC-123"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.QA,
        )

        entity = BacklogReviewDeliberationRequest.build_for_role(
            task_description_entity=task_description,
            role=BacklogReviewRole.QA,
        )

        result = BacklogReviewDeliberationMapper.to_deliberation_request(entity)

        assert result.role == "QA"
        assert "testability" in result.constraints.rubric.lower()

    def test_to_deliberation_request_devops(self) -> None:
        """Test conversion for DEVOPS role."""
        task_description = BacklogReviewTaskDescription.build_without_context(
            ceremony_id=BacklogReviewCeremonyId("BRC-123"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.DEVOPS,
        )

        entity = BacklogReviewDeliberationRequest.build_for_role(
            task_description_entity=task_description,
            role=BacklogReviewRole.DEVOPS,
        )

        result = BacklogReviewDeliberationMapper.to_deliberation_request(entity)

        assert result.role == "DEVOPS"
        assert "infrastructure" in result.constraints.rubric.lower()

    def test_to_deliberation_request_converts_constraints(self) -> None:
        """Test that domain constraints are converted to port constraints."""
        task_description = BacklogReviewTaskDescription.build_without_context(
            ceremony_id=BacklogReviewCeremonyId("BRC-123"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.ARCHITECT,
        )

        entity = BacklogReviewDeliberationRequest.build_for_role(
            task_description_entity=task_description,
            role=BacklogReviewRole.ARCHITECT,
        )

        result = BacklogReviewDeliberationMapper.to_deliberation_request(entity)

        # Verify constraints are converted correctly
        assert isinstance(result.constraints, TaskConstraints)
        assert result.constraints.rubric == entity.constraints.rubric
        assert result.constraints.requirements == entity.constraints.requirements
        assert result.constraints.timeout_seconds == entity.constraints.timeout_seconds
        assert result.constraints.max_iterations == entity.constraints.max_iterations

    def test_to_deliberation_request_converts_task_description(self) -> None:
        """Test that task description is converted to string."""
        task_description = BacklogReviewTaskDescription.build_with_context(
            ceremony_id=BacklogReviewCeremonyId("BRC-123"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.ARCHITECT,
            context_text="Test context",
        )

        entity = BacklogReviewDeliberationRequest.build_for_role(
            task_description_entity=task_description,
            role=BacklogReviewRole.ARCHITECT,
        )

        result = BacklogReviewDeliberationMapper.to_deliberation_request(entity)

        assert isinstance(result.task_description, str)
        assert len(result.task_description) > 0
        assert "ST-001" in result.task_description

    def test_to_deliberation_request_converts_role_enum(self) -> None:
        """Test that role enum is converted to string."""
        task_description = BacklogReviewTaskDescription.build_without_context(
            ceremony_id=BacklogReviewCeremonyId("BRC-123"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.QA,
        )

        entity = BacklogReviewDeliberationRequest.build_for_role(
            task_description_entity=task_description,
            role=BacklogReviewRole.QA,
        )

        result = BacklogReviewDeliberationMapper.to_deliberation_request(entity)

        assert result.role == "QA"
        assert isinstance(result.role, str)

