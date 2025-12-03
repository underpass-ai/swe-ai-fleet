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
    - PO approval context (notes, concerns, priority adjustments)

    Domain Invariants:
    - story_id cannot be empty
    - approval_status must be valid
    - If approved, approved_by and approved_at must be set
    - If approved, po_notes must be provided (PO must explain why)
    - If rejected, approved_by and approved_at must be None
    - If priority_adjustment is provided, po_priority_reason should explain why

    Semantic Context:
    - po_notes: PO explains WHY they approve the plan (business justification)
    - po_concerns: PO notes any risks or concerns to monitor
    - priority_adjustment: PO can override priority (HIGH, MEDIUM, LOW)
    - po_priority_reason: PO explains WHY priority was adjusted
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
    po_notes: str | None = None  # PO explains WHY they approve
    po_concerns: str | None = None  # PO notes risks or things to monitor
    priority_adjustment: str | None = None  # HIGH, MEDIUM, LOW
    po_priority_reason: str | None = None  # WHY priority was adjusted

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
            if not self.po_notes or not self.po_notes.strip():
                raise ValueError(
                    "Approved review must have po_notes explaining WHY PO approved. "
                    "This is required for traceability and knowledge graph."
                )

        if self.approval_status.is_rejected():
            if self.approved_by is not None:
                raise ValueError("Rejected review cannot have approved_by")
            if self.approved_at is not None:
                raise ValueError("Rejected review cannot have approved_at")
            if self.po_notes is not None:
                raise ValueError("Rejected review cannot have po_notes")

        # If priority is adjusted, reason should be provided
        if self.priority_adjustment and not self.po_priority_reason:
            raise ValueError(
                "If priority_adjustment is provided, po_priority_reason must explain WHY"
            )

        # Validate priority_adjustment values
        if self.priority_adjustment and self.priority_adjustment not in (
            "HIGH",
            "MEDIUM",
            "LOW",
        ):
            raise ValueError(
                f"Invalid priority_adjustment: {self.priority_adjustment}. "
                "Must be HIGH, MEDIUM, or LOW"
            )

    def approve(
        self,
        approved_by: UserName,
        approved_at: datetime,
        po_notes: str,
        po_concerns: str | None = None,
        priority_adjustment: str | None = None,
        po_priority_reason: str | None = None,
    ) -> "StoryReviewResult":
        """
        Approve this review result (creates new instance).

        Args:
            approved_by: User who approved
            approved_at: Timestamp of approval
            po_notes: PO explains WHY they approve (REQUIRED for traceability)
            po_concerns: Optional PO concerns or risks to monitor
            priority_adjustment: Optional priority override (HIGH, MEDIUM, LOW)
            po_priority_reason: Required if priority_adjustment is provided

        Returns:
            New StoryReviewResult with approval_status=APPROVED

        Raises:
            ValueError: If approval is not allowed or validation fails
        """
        if not self.approval_status.is_pending():
            raise ValueError(
                f"Cannot approve review in status {self.approval_status.to_string()}"
            )

        if not po_notes or not po_notes.strip():
            raise ValueError(
                "po_notes is required when approving. PO must explain WHY they approve "
                "for traceability and knowledge graph."
            )

        if priority_adjustment and not po_priority_reason:
            raise ValueError(
                "po_priority_reason is required when priority_adjustment is provided"
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
            po_notes=po_notes,
            po_concerns=po_concerns,
            priority_adjustment=priority_adjustment,
            po_priority_reason=po_priority_reason,
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


