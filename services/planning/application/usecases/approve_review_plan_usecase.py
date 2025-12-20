"""ApproveReviewPlanUseCase - PO approves plan preliminary.

Use Case (Application Layer):
- PO approves a plan from ceremony review (Human-in-the-Loop)
- Creates official Plan entity
- Transitions story to READY_FOR_PLANNING
- Publishes planning.plan.approved event
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from planning.application.ports import MessagingPort, StoragePort
from planning.application.usecases.add_stories_to_review_usecase import (
    CeremonyNotFoundError,
)
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.entities.plan import Plan
from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.plan_approval import PlanApproval

logger = logging.getLogger(__name__)


@dataclass
class ApproveReviewPlanUseCase:
    """
    Approve plan preliminary and create official Plan.

    This use case (Human-in-the-Loop):
    1. Retrieves ceremony
    2. Finds StoryReviewResult for story
    3. Approves review result (sets approval_status=APPROVED)
    4. Converts PlanPreliminary → Plan (official entity)
    5. Saves Plan to storage
    6. Updates story status to READY_FOR_PLANNING
    7. Updates ceremony with approved result
    8. Publishes planning.plan.approved event
    9. Returns created Plan

    Following Hexagonal Architecture:
    - Depends on StoragePort and MessagingPort
    - Returns domain entity (Plan)
    """

    storage: StoragePort
    messaging: MessagingPort

    async def execute(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        approval: PlanApproval,
    ) -> tuple[Plan, BacklogReviewCeremony]:
        """
        Approve plan preliminary and create official Plan with PO context.

        This use case (Human-in-the-Loop with Semantic Context):
        1. Retrieves ceremony and finds review result
        2. Approves result with PO context (WHY approved - semantic traceability)
        3. Creates official Plan entity
        4. Creates high-level tasks WITH decision metadata
        5. Persists tasks with semantic relationships (HAS_TASK with decision properties)
        6. Updates ceremony
        7. Publishes event with PO context

        Args:
            ceremony_id: ID of ceremony
            story_id: Story whose plan is being approved
            approval: PlanApproval value object encapsulating PO decision context
                     (who approved, why, concerns, priority adjustments)

        Returns:
            Tuple of (Created Plan entity, Updated BacklogReviewCeremony)

        Raises:
            CeremonyNotFoundError: If ceremony not found
            ValueError: If story not in ceremony, no plan preliminary, not pending,
                       or approval validation fails
            StorageError: If persistence fails
        """
        # Retrieve ceremony
        ceremony = await self.storage.get_backlog_review_ceremony(ceremony_id)

        if not ceremony:
            raise CeremonyNotFoundError(
                f"Ceremony not found: {ceremony_id.value}"
            )

        # Find review result for story
        review_result = None
        for result in ceremony.review_results:
            if result.story_id == story_id:
                review_result = result
                break

        if not review_result:
            raise ValueError(
                f"No review result found for story {story_id.value} "
                f"in ceremony {ceremony_id.value}"
            )

        if not review_result.plan_preliminary:
            raise ValueError(
                f"No plan preliminary found for story {story_id.value}"
            )

        # Approve review result with PO context (immutably)
        approved_at = datetime.now(UTC)
        approved_result = review_result.approve(
            approved_by=approval.approved_by,
            approved_at=approved_at,
            po_notes=approval.po_notes,
            po_concerns=approval.po_concerns,
            priority_adjustment=approval.priority_adjustment,
            po_priority_reason=approval.po_priority_reason,
        )

        # Convert PlanPreliminary → Plan (official entity)
        plan_preliminary = review_result.plan_preliminary
        plan_id = PlanId(f"PL-{uuid4()}")

        plan = Plan(
            plan_id=plan_id,
            story_ids=(story_id,),  # Plan covers this story
            title=plan_preliminary.title,
            description=plan_preliminary.description,
            acceptance_criteria=plan_preliminary.acceptance_criteria,
            technical_notes=plan_preliminary.technical_notes,
            roles=plan_preliminary.roles,
        )

        # Save Plan
        await self.storage.save_plan(plan)

        # Create high-level tasks WITH decision metadata (if available)
        tasks_created = 0
        if plan_preliminary.task_decisions:
            logger.info(
                f"Creating {len(plan_preliminary.task_decisions)} tasks "
                f"with semantic decision metadata for plan {plan_id.value}"
            )

            for task_decision in plan_preliminary.task_decisions:
                # Create Task entity
                from planning.domain.value_objects.content.brief import Brief
                from planning.domain.value_objects.content.title import Title
                from planning.domain.value_objects.identifiers.task_id import TaskId
                from planning.domain.value_objects.statuses.task_status import TaskStatus
                from planning.domain.value_objects.statuses.task_type import TaskType

                task_id = TaskId(f"TSK-{uuid4()}")
                task = Task(
                    task_id=task_id,
                    story_id=story_id,
                    plan_id=plan_id,
                    title=Title(task_decision.task_description),
                    description=Brief(task_decision.decision_reason),
                    type=TaskType.BACKLOG_REVIEW_IDENTIFIED,
                    status=TaskStatus("PENDING"),
                    assigned_to=None,
                    estimated_hours=None,  # Estimated in Planning Meeting
                    priority=task_decision.task_index + 1,
                )

                # Save task WITH semantic relationship
                await self.storage.save_task_with_decision(
                    task=task,
                    decision_metadata={
                        "decided_by": task_decision.decided_by,
                        "decision_reason": task_decision.decision_reason,
                        "council_feedback": task_decision.council_feedback,
                        "source": "BACKLOG_REVIEW",
                        "decided_at": task_decision.decided_at.isoformat(),
                    },
                )

                tasks_created += 1

            logger.info(
                f"Created {tasks_created} tasks with decision context for plan {plan_id.value}"
            )

        # Update story to READY_FOR_PLANNING
        # NOTE: This assumes TransitionStoryUseCase exists
        # For now, we'll just save the plan and ceremony
        # The story transition will be handled separately or via event

        # Update ceremony with approved result
        ceremony = ceremony.update_review_result(story_id, approved_result, approved_at)

        # Persist ceremony
        await self.storage.save_backlog_review_ceremony(ceremony)

        logger.info(
            f"Approved plan {plan_id.value} for story {story_id.value} "
            f"by {approval.approved_by.value} with PO notes: {approval.po_notes[:50]}..."
        )

        # Publish event with PO context (best-effort)
        try:
            await self.messaging.publish(
                subject="planning.plan.approved",
                payload={
                    "ceremony_id": ceremony_id.value,
                    "story_id": story_id.value,
                    "plan_id": plan_id.value,
                    "approved_by": approval.approved_by.value,
                    "approved_at": approved_at.isoformat(),
                    "tasks_outline": list(plan_preliminary.tasks_outline),
                    "estimated_complexity": plan_preliminary.estimated_complexity,
                    "tasks_created": tasks_created,
                    # PO approval context (semantic) - from value object
                    "po_notes": approval.po_notes,
                    "po_concerns": approval.po_concerns,
                    "priority_adjustment": approval.priority_adjustment,
                    "po_priority_reason": approval.po_priority_reason,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to publish plan.approved event: {e}")

        return plan, ceremony

