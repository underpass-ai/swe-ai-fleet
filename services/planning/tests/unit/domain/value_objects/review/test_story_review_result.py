"""Unit tests for StoryReviewResult value object."""

from datetime import UTC, datetime

import pytest
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.plan_preliminary import PlanPreliminary
from planning.domain.value_objects.review.story_review_result import StoryReviewResult
from planning.domain.value_objects.statuses.review_approval_status import (
    ReviewApprovalStatus,
    ReviewApprovalStatusEnum,
)


class TestStoryReviewResult:
    """Test suite for StoryReviewResult value object."""

    @pytest.fixture
    def sample_plan(self) -> PlanPreliminary:
        """Fixture providing a sample PlanPreliminary."""
        return PlanPreliminary(
            title=Title("Auth Plan"),
            description=Brief("Implement authentication"),
            acceptance_criteria=("User can login",),
            technical_notes="Use JWT",
            roles=("DEVELOPER", "QA"),
            estimated_complexity="MEDIUM",
            dependencies=("Redis",),
        )

    @pytest.fixture
    def sample_pending_result(self, sample_plan: PlanPreliminary) -> StoryReviewResult:
        """Fixture providing a sample pending review result."""
        return StoryReviewResult(
            story_id=StoryId("ST-123"),
            plan_preliminary=sample_plan,
            architect_feedback="Looks good architecturally",
            qa_feedback="Testable design",
            devops_feedback="Infrastructure is feasible",
            recommendations=("Add error handling", "Consider rate limiting"),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )

    def test_create_pending_result(self, sample_plan: PlanPreliminary) -> None:
        """Test creating a pending review result."""
        result = StoryReviewResult(
            story_id=StoryId("ST-123"),
            plan_preliminary=sample_plan,
            architect_feedback="Good architecture",
            qa_feedback="Good testability",
            devops_feedback="Good infrastructure",
            recommendations=("Recommendation 1",),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )

        assert result.story_id.value == "ST-123"
        assert result.plan_preliminary == sample_plan
        assert result.approval_status.is_pending()
        assert result.approved_by is None
        assert result.approved_at is None

    def test_create_pending_result_without_plan(self) -> None:
        """Test creating pending result without plan (plan_preliminary is None)."""
        result = StoryReviewResult(
            story_id=StoryId("ST-123"),
            plan_preliminary=None,  # No plan yet
            architect_feedback="Needs more details",
            qa_feedback="Cannot test yet",
            devops_feedback="Not ready",
            recommendations=("Add more details",),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )

        assert result.plan_preliminary is None
        assert result.approval_status.is_pending()

    def test_approve_success(self, sample_pending_result: StoryReviewResult) -> None:
        """Test successfully approving a pending result."""
        approved_by = UserName("po@example.com")
        approved_at = datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC)

        approved_result = sample_pending_result.approve(approved_by, approved_at)

        assert approved_result.approval_status.is_approved()
        assert approved_result.approved_by == approved_by
        assert approved_result.approved_at == approved_at
        # Original fields unchanged
        assert approved_result.story_id == sample_pending_result.story_id
        assert approved_result.architect_feedback == sample_pending_result.architect_feedback

    def test_approve_creates_new_instance(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test that approve() creates a new instance (immutability)."""
        approved_by = UserName("po@example.com")
        approved_at = datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC)

        approved_result = sample_pending_result.approve(approved_by, approved_at)

        # Original unchanged
        assert sample_pending_result.approval_status.is_pending()
        assert sample_pending_result.approved_by is None
        # New instance created
        assert approved_result.approval_status.is_approved()
        assert approved_result.approved_by is not None

    def test_approve_already_approved_raises_value_error(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test that approving an already approved result raises ValueError."""
        approved_result = sample_pending_result.approve(
            UserName("po@example.com"),
            datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
        )

        with pytest.raises(ValueError, match="Cannot approve review in status"):
            approved_result.approve(
                UserName("po@example.com"),
                datetime(2025, 12, 2, 13, 0, 0, tzinfo=UTC),
            )

    def test_approve_rejected_result_raises_value_error(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test that approving a rejected result raises ValueError."""
        rejected_result = sample_pending_result.reject()

        with pytest.raises(ValueError, match="Cannot approve review in status"):
            rejected_result.approve(
                UserName("po@example.com"),
                datetime(2025, 12, 2, 13, 0, 0, tzinfo=UTC),
            )

    def test_reject_success(self, sample_pending_result: StoryReviewResult) -> None:
        """Test successfully rejecting a pending result."""
        rejected_result = sample_pending_result.reject()

        assert rejected_result.approval_status.is_rejected()
        assert rejected_result.approved_by is None
        assert rejected_result.approved_at is None
        # Original fields unchanged
        assert rejected_result.story_id == sample_pending_result.story_id

    def test_reject_creates_new_instance(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test that reject() creates a new instance (immutability)."""
        rejected_result = sample_pending_result.reject()

        # Original unchanged
        assert sample_pending_result.approval_status.is_pending()
        # New instance created
        assert rejected_result.approval_status.is_rejected()

    def test_reject_already_rejected_raises_value_error(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test that rejecting an already rejected result raises ValueError."""
        rejected_result = sample_pending_result.reject()

        with pytest.raises(ValueError, match="Cannot reject review in status"):
            rejected_result.reject()

    def test_reject_approved_result_raises_value_error(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test that rejecting an approved result raises ValueError."""
        approved_result = sample_pending_result.approve(
            UserName("po@example.com"),
            datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
        )

        with pytest.raises(ValueError, match="Cannot reject review in status"):
            approved_result.reject()

    def test_post_init_approved_requires_approved_by(
        self, sample_plan: PlanPreliminary
    ) -> None:
        """Test that approved status requires approved_by."""
        with pytest.raises(ValueError, match="Approved review must have approved_by"):
            StoryReviewResult(
                story_id=StoryId("ST-123"),
                plan_preliminary=sample_plan,
                architect_feedback="Good",
                qa_feedback="Good",
                devops_feedback="Good",
                recommendations=(),
                approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.APPROVED),
                reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
                approved_by=None,  # Missing!
                approved_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
            )

    def test_post_init_approved_requires_approved_at(
        self, sample_plan: PlanPreliminary
    ) -> None:
        """Test that approved status requires approved_at."""
        with pytest.raises(ValueError, match="Approved review must have approved_at"):
            StoryReviewResult(
                story_id=StoryId("ST-123"),
                plan_preliminary=sample_plan,
                architect_feedback="Good",
                qa_feedback="Good",
                devops_feedback="Good",
                recommendations=(),
                approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.APPROVED),
                reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
                approved_by=UserName("po@example.com"),
                approved_at=None,  # Missing!
            )

    def test_post_init_rejected_cannot_have_approved_by(
        self, sample_plan: PlanPreliminary
    ) -> None:
        """Test that rejected status cannot have approved_by."""
        with pytest.raises(ValueError, match="Rejected review cannot have approved_by"):
            StoryReviewResult(
                story_id=StoryId("ST-123"),
                plan_preliminary=sample_plan,
                architect_feedback="Good",
                qa_feedback="Good",
                devops_feedback="Good",
                recommendations=(),
                approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.REJECTED),
                reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
                approved_by=UserName("po@example.com"),  # Should be None!
                approved_at=None,
            )

    def test_post_init_rejected_cannot_have_approved_at(
        self, sample_plan: PlanPreliminary
    ) -> None:
        """Test that rejected status cannot have approved_at."""
        with pytest.raises(ValueError, match="Rejected review cannot have approved_at"):
            StoryReviewResult(
                story_id=StoryId("ST-123"),
                plan_preliminary=sample_plan,
                architect_feedback="Good",
                qa_feedback="Good",
                devops_feedback="Good",
                recommendations=(),
                approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.REJECTED),
                reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
                approved_by=None,
                approved_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),  # Should be None!
            )

    def test_str_representation(self, sample_pending_result: StoryReviewResult) -> None:
        """Test __str__ returns meaningful representation."""
        str_repr = str(sample_pending_result)

        assert "ST-123" in str_repr
        assert "PENDING" in str_repr

    def test_empty_recommendations_allowed(self, sample_plan: PlanPreliminary) -> None:
        """Test that empty recommendations tuple is allowed."""
        result = StoryReviewResult(
            story_id=StoryId("ST-123"),
            plan_preliminary=sample_plan,
            architect_feedback="Good",
            qa_feedback="Good",
            devops_feedback="Good",
            recommendations=(),  # Empty is OK
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )

        assert result.recommendations == ()

    def test_multiple_recommendations(self, sample_plan: PlanPreliminary) -> None:
        """Test result with multiple recommendations."""
        result = StoryReviewResult(
            story_id=StoryId("ST-123"),
            plan_preliminary=sample_plan,
            architect_feedback="Good",
            qa_feedback="Good",
            devops_feedback="Good",
            recommendations=(
                "Add error handling",
                "Consider rate limiting",
                "Add logging",
            ),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )

        assert len(result.recommendations) == 3

    def test_immutability(self, sample_pending_result: StoryReviewResult) -> None:
        """Test that StoryReviewResult is immutable (frozen dataclass)."""
        with pytest.raises(AttributeError):
            sample_pending_result.architect_feedback = "Changed"  # type: ignore

