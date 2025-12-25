"""Unit tests for StoryReviewResult value object."""

from datetime import UTC, datetime

import pytest
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.plan_preliminary import PlanPreliminary
from planning.domain.value_objects.review.story_review_result import StoryReviewResult
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)
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
        po_notes = "Approved because critical for MVP"
        plan_id = PlanId("PL-12345")

        approved_result = sample_pending_result.approve(
            approved_by,
            approved_at,
            po_notes,
            plan_id=plan_id,
        )

        assert approved_result.approval_status.is_approved()
        assert approved_result.approved_by == approved_by
        assert approved_result.approved_at == approved_at
        assert approved_result.po_notes == po_notes
        assert approved_result.plan_id == plan_id
        # Original fields unchanged
        assert approved_result.story_id == sample_pending_result.story_id
        assert approved_result.architect_feedback == sample_pending_result.architect_feedback

    def test_approve_creates_new_instance(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test that approve() creates a new instance (immutability)."""
        approved_by = UserName("po@example.com")
        approved_at = datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC)
        po_notes = "Approved"

        approved_result = sample_pending_result.approve(approved_by, approved_at, po_notes)

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
            po_notes="Approved",
        )

        with pytest.raises(ValueError, match="Cannot approve review in status"):
            approved_result.approve(
                UserName("po@example.com"),
                datetime(2025, 12, 2, 13, 0, 0, tzinfo=UTC),
                po_notes="Approved again",
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
                po_notes="Approved",
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
            po_notes="Approved",
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

    def test_create_from_role_feedback_architect(self) -> None:
        """Test creating StoryReviewResult from ARCHITECT feedback."""
        story_id = StoryId("ST-123")
        feedback = "Technical analysis: The architecture looks solid"
        tasks = ("Setup infrastructure", "Implement core feature")
        reviewed_at = datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC)

        result = StoryReviewResult.create_from_role_feedback(
            story_id=story_id,
            role=BacklogReviewRole.ARCHITECT,
            feedback=feedback,
            tasks_outline=tasks,
            reviewed_at=reviewed_at,
        )

        assert result.story_id == story_id
        assert result.architect_feedback == feedback
        assert result.qa_feedback == ""
        assert result.devops_feedback == ""
        assert result.plan_preliminary is not None
        assert result.plan_preliminary.tasks_outline == tasks
        assert BacklogReviewRole.ARCHITECT.value in result.plan_preliminary.roles
        assert result.approval_status.is_pending()
        assert result.reviewed_at == reviewed_at

    def test_create_from_role_feedback_qa(self) -> None:
        """Test creating StoryReviewResult from QA feedback."""
        story_id = StoryId("ST-456")
        feedback = "Testability assessment: Good test coverage possible"
        tasks = ("Write unit tests", "Add integration tests")
        reviewed_at = datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC)

        result = StoryReviewResult.create_from_role_feedback(
            story_id=story_id,
            role=BacklogReviewRole.QA,
            feedback=feedback,
            tasks_outline=tasks,
            reviewed_at=reviewed_at,
        )

        assert result.qa_feedback == feedback
        assert result.architect_feedback == ""
        assert result.devops_feedback == ""
        assert BacklogReviewRole.QA.value in result.plan_preliminary.roles

    def test_create_from_role_feedback_devops(self) -> None:
        """Test creating StoryReviewResult from DEVOPS feedback."""
        story_id = StoryId("ST-789")
        feedback = "Infrastructure review: Deployment pipeline ready"
        tasks = ("Configure CI/CD", "Setup monitoring")
        reviewed_at = datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC)

        result = StoryReviewResult.create_from_role_feedback(
            story_id=story_id,
            role=BacklogReviewRole.DEVOPS,
            feedback=feedback,
            tasks_outline=tasks,
            reviewed_at=reviewed_at,
        )

        assert result.devops_feedback == feedback
        assert result.architect_feedback == ""
        assert result.qa_feedback == ""
        assert BacklogReviewRole.DEVOPS.value in result.plan_preliminary.roles

    def test_create_from_role_feedback_long_description(self) -> None:
        """Test that long feedback is truncated in description."""
        long_feedback = "A" * 300  # 300 characters
        result = StoryReviewResult.create_from_role_feedback(
            story_id=StoryId("ST-123"),
            role=BacklogReviewRole.ARCHITECT,
            feedback=long_feedback,
            tasks_outline=(),
            reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )

        # Description should be truncated to 200 characters
        assert len(result.plan_preliminary.description.value) == 200
        # But full feedback should be preserved
        assert len(result.architect_feedback) == 300

    def test_create_from_role_feedback_creates_plan_preliminary(self) -> None:
        """Test that factory method creates PlanPreliminary with defaults."""
        result = StoryReviewResult.create_from_role_feedback(
            story_id=StoryId("ST-123"),
            role=BacklogReviewRole.ARCHITECT,
            feedback="Feedback",
            tasks_outline=("Task 1", "Task 2"),
            reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )

        assert result.plan_preliminary is not None
        assert "ST-123" in result.plan_preliminary.title.value
        assert result.plan_preliminary.estimated_complexity == "MEDIUM"
        assert len(result.plan_preliminary.acceptance_criteria) > 0
        assert result.plan_preliminary.tasks_outline == ("Task 1", "Task 2")

    def test_post_init_approved_requires_po_notes(
        self, sample_plan: PlanPreliminary
    ) -> None:
        """Test that approved status requires non-empty po_notes."""
        with pytest.raises(ValueError, match="Approved review must have po_notes"):
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
                approved_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
                po_notes="",  # Empty!
            )

    def test_post_init_approved_requires_po_notes_not_whitespace(
        self, sample_plan: PlanPreliminary
    ) -> None:
        """Test that approved status requires po_notes not just whitespace."""
        with pytest.raises(ValueError, match="Approved review must have po_notes"):
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
                approved_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
                po_notes="   ",  # Only whitespace!
            )

    def test_post_init_rejected_cannot_have_po_notes(
        self, sample_plan: PlanPreliminary
    ) -> None:
        """Test that rejected status cannot have po_notes."""
        with pytest.raises(ValueError, match="Rejected review cannot have po_notes"):
            StoryReviewResult(
                story_id=StoryId("ST-123"),
                plan_preliminary=sample_plan,
                architect_feedback="Good",
                qa_feedback="Good",
                devops_feedback="Good",
                recommendations=(),
                approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.REJECTED),
                reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
                po_notes="Some notes",  # Should be None!
            )

    def test_post_init_priority_adjustment_requires_reason(
        self, sample_plan: PlanPreliminary
    ) -> None:
        """Test that priority_adjustment requires po_priority_reason."""
        with pytest.raises(
            ValueError, match="po_priority_reason must explain WHY"
        ):
            StoryReviewResult(
                story_id=StoryId("ST-123"),
                plan_preliminary=sample_plan,
                architect_feedback="Good",
                qa_feedback="Good",
                devops_feedback="Good",
                recommendations=(),
                approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
                reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
                priority_adjustment="HIGH",
                po_priority_reason=None,  # Missing!
            )

    def test_post_init_priority_adjustment_invalid_value(
        self, sample_plan: PlanPreliminary
    ) -> None:
        """Test that priority_adjustment must be HIGH, MEDIUM, or LOW."""
        with pytest.raises(ValueError, match="Invalid priority_adjustment"):
            StoryReviewResult(
                story_id=StoryId("ST-123"),
                plan_preliminary=sample_plan,
                architect_feedback="Good",
                qa_feedback="Good",
                devops_feedback="Good",
                recommendations=(),
                approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
                reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
                priority_adjustment="CRITICAL",  # Invalid!
                po_priority_reason="Reason",
            )

    def test_post_init_priority_adjustment_valid_values(
        self, sample_plan: PlanPreliminary
    ) -> None:
        """Test that valid priority_adjustment values are accepted."""
        for priority in ("HIGH", "MEDIUM", "LOW"):
            result = StoryReviewResult(
                story_id=StoryId("ST-123"),
                plan_preliminary=sample_plan,
                architect_feedback="Good",
                qa_feedback="Good",
                devops_feedback="Good",
                recommendations=(),
                approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
                reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
                priority_adjustment=priority,
                po_priority_reason="Reason for adjustment",
            )
            assert result.priority_adjustment == priority

    def test_approve_with_empty_po_notes_raises_error(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test that approve() requires non-empty po_notes."""
        with pytest.raises(ValueError, match="po_notes is required when approving"):
            sample_pending_result.approve(
                approved_by=UserName("po@example.com"),
                approved_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
                po_notes="",  # Empty!
            )

    def test_approve_with_whitespace_po_notes_raises_error(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test that approve() requires po_notes not just whitespace."""
        with pytest.raises(ValueError, match="po_notes is required when approving"):
            sample_pending_result.approve(
                approved_by=UserName("po@example.com"),
                approved_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
                po_notes="   ",  # Only whitespace!
            )

    def test_approve_with_priority_adjustment_requires_reason(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test that approve() requires po_priority_reason when priority_adjustment provided."""
        with pytest.raises(
            ValueError, match="po_priority_reason is required when priority_adjustment"
        ):
            sample_pending_result.approve(
                approved_by=UserName("po@example.com"),
                approved_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
                po_notes="Approved",
                priority_adjustment="HIGH",
                po_priority_reason=None,  # Missing!
            )

    def test_approve_with_priority_adjustment_success(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test successfully approving with priority adjustment."""
        plan_id = PlanId("PL-67890")
        approved_result = sample_pending_result.approve(
            approved_by=UserName("po@example.com"),
            approved_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
            po_notes="Approved for MVP",
            priority_adjustment="HIGH",
            po_priority_reason="Critical for launch",
            plan_id=plan_id,
        )

        assert approved_result.approval_status.is_approved()
        assert approved_result.priority_adjustment == "HIGH"
        assert approved_result.po_priority_reason == "Critical for launch"
        assert approved_result.plan_id == plan_id

    def test_approve_with_po_concerns(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test approving with optional po_concerns."""
        plan_id = PlanId("PL-11111")
        approved_result = sample_pending_result.approve(
            approved_by=UserName("po@example.com"),
            approved_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
            po_notes="Approved",
            po_concerns="Monitor performance",
            plan_id=plan_id,
        )

        assert approved_result.po_concerns == "Monitor performance"
        assert approved_result.plan_id == plan_id

    def test_add_role_feedback_raises_error_when_no_plan(
        self, sample_plan: PlanPreliminary
    ) -> None:
        """Test that add_role_feedback raises error when plan_preliminary is None."""
        result = StoryReviewResult(
            story_id=StoryId("ST-123"),
            plan_preliminary=None,  # No plan!
            architect_feedback="",
            qa_feedback="",
            devops_feedback="",
            recommendations=(),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )

        with pytest.raises(
            ValueError, match="Cannot add role feedback to result without plan_preliminary"
        ):
            result.add_role_feedback(
                role=BacklogReviewRole.ARCHITECT,
                feedback="New feedback",
                tasks_outline=("Task 1",),
                reviewed_at=datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC),
            )

    def test_add_role_feedback_architect(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test adding ARCHITECT feedback updates architect_feedback."""
        new_feedback = "Updated architect feedback"
        new_tasks = ("New task 1", "New task 2")
        reviewed_at = datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC)

        updated_result = sample_pending_result.add_role_feedback(
            role=BacklogReviewRole.ARCHITECT,
            feedback=new_feedback,
            tasks_outline=new_tasks,
            reviewed_at=reviewed_at,
        )

        assert updated_result.architect_feedback == new_feedback
        assert updated_result.qa_feedback == sample_pending_result.qa_feedback
        assert updated_result.devops_feedback == sample_pending_result.devops_feedback
        assert updated_result.reviewed_at == reviewed_at
        # Check tasks are merged
        assert "New task 1" in updated_result.plan_preliminary.tasks_outline
        assert "New task 2" in updated_result.plan_preliminary.tasks_outline
        # Check role is added
        assert BacklogReviewRole.ARCHITECT.value in updated_result.plan_preliminary.roles

    def test_add_role_feedback_qa(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test adding QA feedback updates qa_feedback."""
        new_feedback = "Updated QA feedback"
        new_tasks = ("Test task",)
        reviewed_at = datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC)

        updated_result = sample_pending_result.add_role_feedback(
            role=BacklogReviewRole.QA,
            feedback=new_feedback,
            tasks_outline=new_tasks,
            reviewed_at=reviewed_at,
        )

        assert updated_result.qa_feedback == new_feedback
        assert updated_result.architect_feedback == sample_pending_result.architect_feedback
        assert updated_result.devops_feedback == sample_pending_result.devops_feedback
        assert BacklogReviewRole.QA.value in updated_result.plan_preliminary.roles

    def test_add_role_feedback_devops(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test adding DEVOPS feedback updates devops_feedback."""
        new_feedback = "Updated DevOps feedback"
        new_tasks = ("Deploy task",)
        reviewed_at = datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC)

        updated_result = sample_pending_result.add_role_feedback(
            role=BacklogReviewRole.DEVOPS,
            feedback=new_feedback,
            tasks_outline=new_tasks,
            reviewed_at=reviewed_at,
        )

        assert updated_result.devops_feedback == new_feedback
        assert updated_result.architect_feedback == sample_pending_result.architect_feedback
        assert updated_result.qa_feedback == sample_pending_result.qa_feedback
        assert BacklogReviewRole.DEVOPS.value in updated_result.plan_preliminary.roles

    def test_add_role_feedback_merges_tasks_deduplicates(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test that add_role_feedback merges and deduplicates tasks."""
        # Add tasks that might overlap
        new_tasks = ("Task 1", "Task 2", "Task 1")  # Duplicate Task 1
        reviewed_at = datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC)

        updated_result = sample_pending_result.add_role_feedback(
            role=BacklogReviewRole.ARCHITECT,
            feedback="Feedback",
            tasks_outline=new_tasks,
            reviewed_at=reviewed_at,
        )

        # Should deduplicate
        task_list = list(updated_result.plan_preliminary.tasks_outline)
        assert task_list.count("Task 1") == 1  # Deduplicated
        assert "Task 2" in task_list

    def test_add_role_feedback_preserves_other_fields(
        self, sample_pending_result: StoryReviewResult
    ) -> None:
        """Test that add_role_feedback preserves all other fields."""
        updated_result = sample_pending_result.add_role_feedback(
            role=BacklogReviewRole.ARCHITECT,
            feedback="New feedback",
            tasks_outline=("Task 1",),
            reviewed_at=datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC),
        )

        # All other fields should be preserved
        assert updated_result.story_id == sample_pending_result.story_id
        assert updated_result.recommendations == sample_pending_result.recommendations
        assert updated_result.approval_status == sample_pending_result.approval_status
        assert updated_result.approved_by == sample_pending_result.approved_by
        assert updated_result.approved_at == sample_pending_result.approved_at
        assert updated_result.po_notes == sample_pending_result.po_notes
        assert updated_result.po_concerns == sample_pending_result.po_concerns
        assert updated_result.priority_adjustment == sample_pending_result.priority_adjustment
        assert updated_result.po_priority_reason == sample_pending_result.po_priority_reason
        assert updated_result.plan_id == sample_pending_result.plan_id

    def test_approve_with_plan_id(self, sample_pending_result: StoryReviewResult) -> None:
        """Test approving with plan_id."""
        plan_id = PlanId("PL-99999")
        approved_result = sample_pending_result.approve(
            approved_by=UserName("po@example.com"),
            approved_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
            po_notes="Approved",
            plan_id=plan_id,
        )

        assert approved_result.plan_id == plan_id
        assert approved_result.approval_status.is_approved()

    def test_approve_without_plan_id(self, sample_pending_result: StoryReviewResult) -> None:
        """Test approving without plan_id (optional)."""
        approved_result = sample_pending_result.approve(
            approved_by=UserName("po@example.com"),
            approved_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
            po_notes="Approved",
            plan_id=None,
        )

        assert approved_result.plan_id is None
        assert approved_result.approval_status.is_approved()

