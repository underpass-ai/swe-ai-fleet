"""Story Review Result value object."""

from dataclasses import dataclass
from datetime import datetime

from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.agent_deliberation import AgentDeliberation
from planning.domain.value_objects.review.plan_preliminary import PlanPreliminary
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)
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
    approval_status: ReviewApprovalStatus
    reviewed_at: datetime
    recommendations: tuple[str, ...] = ()  # Recommendations from review
    agent_deliberations: tuple[AgentDeliberation, ...] = ()  # All agent deliberations
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
            self._validate_approved_status()
        elif self.approval_status.is_rejected():
            self._validate_rejected_status()

        self._validate_priority_adjustment()

    def _validate_approved_status(self) -> None:
        """Validate approved status requirements."""
        if not self.approved_by:
            raise ValueError("Approved review must have approved_by")
        if not self.approved_at:
            raise ValueError("Approved review must have approved_at")
        if not self.po_notes or not self.po_notes.strip():
            raise ValueError(
                "Approved review must have po_notes explaining WHY PO approved. "
                "This is required for traceability and knowledge graph."
            )

    def _validate_rejected_status(self) -> None:
        """Validate rejected status requirements."""
        if self.approved_by is not None:
            raise ValueError("Rejected review cannot have approved_by")
        if self.approved_at is not None:
            raise ValueError("Rejected review cannot have approved_at")
        if self.po_notes is not None:
            raise ValueError("Rejected review cannot have po_notes")

    def _validate_priority_adjustment(self) -> None:
        """Validate priority adjustment logic."""
        if not self.priority_adjustment:
            return

        if not self.po_priority_reason:
            raise ValueError(
                "If priority_adjustment is provided, po_priority_reason must explain WHY"
            )

        if self.priority_adjustment not in ("HIGH", "MEDIUM", "LOW"):
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

    def add_agent_deliberation(
        self,
        deliberation: AgentDeliberation,
        feedback: str,
        tasks_outline: tuple[str, ...],
        reviewed_at: datetime,
    ) -> "StoryReviewResult":
        """
        Add agent deliberation to review result (creates new instance).

        Domain method following "Tell, Don't Ask" principle.
        Encapsulates the logic of adding agent deliberations and updating role feedback.

        Args:
            deliberation: Agent deliberation to add
            feedback: Feedback text from the agent (extracted from proposal)
            tasks_outline: New tasks identified by this agent
            reviewed_at: Timestamp when review was completed

        Returns:
            New StoryReviewResult with added agent deliberation and updated role feedback

        Raises:
            ValueError: If plan_preliminary is None
        """
        if not self.plan_preliminary:
            raise ValueError("Cannot add agent deliberation to result without plan_preliminary")

        # Add new deliberation to existing list
        updated_deliberations = list(self.agent_deliberations)
        updated_deliberations.append(deliberation)

        # Update feedback for the specific role (aggregate feedback from all agents of this role)
        role = deliberation.role
        architect_feedback = self.architect_feedback
        qa_feedback = self.qa_feedback
        devops_feedback = self.devops_feedback

        if role == BacklogReviewRole.ARCHITECT:
            # Aggregate feedback: append new feedback if existing is not empty
            if architect_feedback:
                architect_feedback = f"{architect_feedback}\n\n--- Agent {deliberation.agent_id} ---\n{feedback}"
            else:
                architect_feedback = feedback
        elif role == BacklogReviewRole.QA:
            if qa_feedback:
                qa_feedback = f"{qa_feedback}\n\n--- Agent {deliberation.agent_id} ---\n{feedback}"
            else:
                qa_feedback = feedback
        elif role == BacklogReviewRole.DEVOPS:
            if devops_feedback:
                devops_feedback = f"{devops_feedback}\n\n--- Agent {deliberation.agent_id} ---\n{feedback}"
            else:
                devops_feedback = feedback

        # Merge tasks (deduplicate)
        existing_tasks = list(self.plan_preliminary.tasks_outline)
        merged_tasks = tuple(set(existing_tasks + list(tasks_outline)))

        # Update roles (convert enum to string for PlanPreliminary)
        existing_roles = set(self.plan_preliminary.roles)
        existing_roles.add(role.value)

        # Update PlanPreliminary
        updated_plan_preliminary = PlanPreliminary(
            title=self.plan_preliminary.title,
            description=self.plan_preliminary.description,
            acceptance_criteria=self.plan_preliminary.acceptance_criteria,
            technical_notes=self.plan_preliminary.technical_notes,
            roles=tuple(existing_roles),
            estimated_complexity=self.plan_preliminary.estimated_complexity,
            dependencies=self.plan_preliminary.dependencies,
            tasks_outline=merged_tasks,
            task_decisions=self.plan_preliminary.task_decisions,
        )

        return StoryReviewResult(
            story_id=self.story_id,
            plan_preliminary=updated_plan_preliminary,
            architect_feedback=architect_feedback,
            qa_feedback=qa_feedback,
            devops_feedback=devops_feedback,
            agent_deliberations=tuple(updated_deliberations),
            recommendations=self.recommendations,
            approval_status=self.approval_status,
            reviewed_at=reviewed_at,
            approved_by=self.approved_by,
            approved_at=self.approved_at,
            po_notes=self.po_notes,
            po_concerns=self.po_concerns,
            priority_adjustment=self.priority_adjustment,
            po_priority_reason=self.po_priority_reason,
        )

    def add_role_feedback(
        self,
        role: BacklogReviewRole,
        feedback: str,
        tasks_outline: tuple[str, ...],
        reviewed_at: datetime,
    ) -> "StoryReviewResult":
        """
        Add or update feedback from a specific role (creates new instance).

        DEPRECATED: Use add_agent_deliberation instead.
        Kept for backward compatibility.

        Domain method following "Tell, Don't Ask" principle.
        Encapsulates the logic of updating role feedback and merging tasks.

        Args:
            role: Council role providing feedback
            feedback: Feedback text from the role
            tasks_outline: New tasks identified by this role
            reviewed_at: Timestamp when review was completed

        Returns:
            New StoryReviewResult with updated role feedback and merged tasks

        Raises:
            ValueError: If plan_preliminary is None
        """
        if not self.plan_preliminary:
            raise ValueError("Cannot add role feedback to result without plan_preliminary")

        # Update feedback for the specific role
        architect_feedback = self.architect_feedback
        qa_feedback = self.qa_feedback
        devops_feedback = self.devops_feedback

        if role == BacklogReviewRole.ARCHITECT:
            architect_feedback = feedback
        elif role == BacklogReviewRole.QA:
            qa_feedback = feedback
        elif role == BacklogReviewRole.DEVOPS:
            devops_feedback = feedback

        # Merge tasks (deduplicate)
        existing_tasks = list(self.plan_preliminary.tasks_outline)
        merged_tasks = tuple(set(existing_tasks + list(tasks_outline)))

        # Update roles (convert enum to string for PlanPreliminary)
        existing_roles = set(self.plan_preliminary.roles)
        existing_roles.add(role.value)

        # Update PlanPreliminary
        updated_plan_preliminary = PlanPreliminary(
            title=self.plan_preliminary.title,
            description=self.plan_preliminary.description,
            acceptance_criteria=self.plan_preliminary.acceptance_criteria,
            technical_notes=self.plan_preliminary.technical_notes,
            roles=tuple(existing_roles),
            estimated_complexity=self.plan_preliminary.estimated_complexity,
            dependencies=self.plan_preliminary.dependencies,
            tasks_outline=merged_tasks,
            task_decisions=self.plan_preliminary.task_decisions,
        )

        return StoryReviewResult(
            story_id=self.story_id,
            plan_preliminary=updated_plan_preliminary,
            architect_feedback=architect_feedback,
            qa_feedback=qa_feedback,
            devops_feedback=devops_feedback,
            agent_deliberations=self.agent_deliberations,  # Preserve existing
            recommendations=self.recommendations,
            approval_status=self.approval_status,
            reviewed_at=reviewed_at,
            approved_by=self.approved_by,
            approved_at=self.approved_at,
            po_notes=self.po_notes,
            po_concerns=self.po_concerns,
            priority_adjustment=self.priority_adjustment,
            po_priority_reason=self.po_priority_reason,
        )

    @classmethod
    def create_from_role_feedback(
        cls,
        story_id: StoryId,
        role: BacklogReviewRole,
        feedback: str,
        tasks_outline: tuple[str, ...],
        reviewed_at: datetime,
    ) -> "StoryReviewResult":
        """
        Create new StoryReviewResult from initial role feedback (factory method).

        Domain factory method following "Tell, Don't Ask" principle.
        Encapsulates the creation logic for a new review result.

        Args:
            story_id: Story being reviewed
            role: Council role providing initial feedback
            feedback: Feedback text from the role
            tasks_outline: Tasks identified by this role
            reviewed_at: Timestamp when review was completed

        Returns:
            New StoryReviewResult with initial role feedback
        """
        # Create PlanPreliminary with initial data
        plan_preliminary = PlanPreliminary(
            title=Title(f"Plan for {story_id.value}"),
            description=Brief(
                feedback[:200] if len(feedback) > 200 else feedback
            ),
            acceptance_criteria=("Council review completed",),
            technical_notes="",
            roles=(role.value,),  # Convert enum to string
            estimated_complexity="MEDIUM",
            dependencies=(),
            tasks_outline=tasks_outline,
        )

        # Set feedback based on role
        architect_feedback = feedback if role == BacklogReviewRole.ARCHITECT else ""
        qa_feedback = feedback if role == BacklogReviewRole.QA else ""
        devops_feedback = feedback if role == BacklogReviewRole.DEVOPS else ""

        return cls(
            story_id=story_id,
            plan_preliminary=plan_preliminary,
            architect_feedback=architect_feedback,
            qa_feedback=qa_feedback,
            devops_feedback=devops_feedback,
            agent_deliberations=(),  # Empty initially, will be populated by add_agent_deliberation
            recommendations=(),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=reviewed_at,
        )

    def has_all_role_deliberations(self) -> bool:
        """
        Check if all roles (ARCHITECT, QA, DEVOPS) have at least one deliberation.

        Returns:
            True if all 3 roles have at least one agent deliberation
        """
        roles_with_deliberations = {d.role for d in self.agent_deliberations}
        required_roles = {
            BacklogReviewRole.ARCHITECT,
            BacklogReviewRole.QA,
            BacklogReviewRole.DEVOPS,
        }
        return required_roles.issubset(roles_with_deliberations)

    def __str__(self) -> str:
        """String representation for logging."""
        return (
            f"StoryReviewResult(story_id={self.story_id}, "
            f"approval_status={self.approval_status.to_string()})"
        )


