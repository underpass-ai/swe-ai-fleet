"""Story Review Result value object."""

from dataclasses import dataclass
from datetime import datetime

from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.plan_preliminary import PlanPreliminary
from planning.domain.value_objects.statuses.review_approval_status import (
    ReviewApprovalStatus,
    ReviewApprovalStatusEnum,
)


@dataclass(frozen=True)
class StoryReviewResult:
    """
    Value Object: Result of reviewing a story by councils.

    Contains:
    - Plan preliminary generated
    - Feedback from each role (Architect, QA, DevOps)
    - Recommendations
    - Approval status (pending, approved, rejected)

    Domain Invariants:
    - story_id cannot be empty
    - approval_status must be valid
    - If approved, approved_by and approved_at must be set
    - If rejected, approved_by and approved_at must be None
    """

    story_id: StoryId
    plan_preliminary: PlanPreliminary | None
    architect_feedback: str
    qa_feedback: str
    devops_feedback: str
    recommendations: tuple[str, ...]
    approval_status: ReviewApprovalStatus
    reviewed_at: datetime
    approved_by: UserName | None = None
    approved_at: datetime | None = None

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Raises:
            ValueError: If validation fails
        """
        if self.approval_status.is_approved():
            if not self.approved_by:
                raise ValueError("Approved review must have approved_by")
            if not self.approved_at:
                raise ValueError("Approved review must have approved_at")

        if self.approval_status.is_rejected():
            if self.approved_by is not None:
                raise ValueError("Rejected review cannot have approved_by")
            if self.approved_at is not None:
                raise ValueError("Rejected review cannot have approved_at")

    def approve(
        self,
        approved_by: UserName,
        approved_at: datetime,
    ) -> "StoryReviewResult":
        """
        Approve this review result (creates new instance).

        Args:
            approved_by: User who approved
            approved_at: Timestamp of approval

        Returns:
            New StoryReviewResult with approval_status=APPROVED
        """
        if not self.approval_status.is_pending():
            raise ValueError(
                f"Cannot approve review in status {self.approval_status.to_string()}"
            )

        return StoryReviewResult(
            story_id=self.story_id,
            plan_preliminary=self.plan_preliminary,
            architect_feedback=self.architect_feedback,
            qa_feedback=self.qa_feedback,
            devops_feedback=self.devops_feedback,
            recommendations=self.recommendations,
            approval_status=ReviewApprovalStatus(
                ReviewApprovalStatusEnum.APPROVED
            ),
            reviewed_at=self.reviewed_at,
            approved_by=approved_by,
            approved_at=approved_at,
        )

    def reject(self) -> "StoryReviewResult":
        """
        Reject this review result (creates new instance).

        Returns:
            New StoryReviewResult with approval_status=REJECTED
        """
        if not self.approval_status.is_pending():
            raise ValueError(
                f"Cannot reject review in status {self.approval_status.to_string()}"
            )

        return StoryReviewResult(
            story_id=self.story_id,
            plan_preliminary=self.plan_preliminary,
            architect_feedback=self.architect_feedback,
            qa_feedback=self.qa_feedback,
            devops_feedback=self.devops_feedback,
            recommendations=self.recommendations,
            approval_status=ReviewApprovalStatus(
                ReviewApprovalStatusEnum.REJECTED
            ),
            reviewed_at=self.reviewed_at,
            approved_by=None,
            approved_at=None,
        )

    def __str__(self) -> str:
        """String representation for logging."""
        return (
            f"StoryReviewResult(story_id={self.story_id}, "
            f"approval_status={self.approval_status.to_string()})"
        )


