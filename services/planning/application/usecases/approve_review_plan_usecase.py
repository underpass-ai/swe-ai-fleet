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
from planning.domain.value_objects.review.plan_preliminary import PlanPreliminary
from planning.domain.value_objects.review.story_review_result import StoryReviewResult

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

    def _find_review_result(
        self, ceremony: BacklogReviewCeremony, story_id: StoryId
    ) -> StoryReviewResult:
        """Find review result for story in ceremony.

        Args:
            ceremony: BacklogReviewCeremony entity
            story_id: Story ID to find review result for

        Returns:
            StoryReviewResult for the story

        Raises:
            ValueError: If review result not found or has no plan preliminary
        """
        review_result = None
        for result in ceremony.review_results:
            if result.story_id == story_id:
                review_result = result
                break

        if not review_result:
            raise ValueError(
                f"No review result found for story {story_id.value} "
                f"in ceremony {ceremony.ceremony_id.value}"
            )

        if not review_result.plan_preliminary:
            raise ValueError(
                f"No plan preliminary found for story {story_id.value}"
            )

        return review_result

    async def _update_existing_tasks_with_plan_id(
        self, story_id: StoryId, plan_id: PlanId
    ) -> int:
        """Update existing tasks with plan_id.

        Args:
            story_id: Story ID to find tasks for
            plan_id: Plan ID to link tasks to

        Returns:
            Number of tasks updated
        """
        existing_tasks = await self.storage.list_tasks(story_id=story_id, limit=1000, offset=0)
        tasks_updated = 0
        for existing_task in existing_tasks:
            if existing_task.plan_id is None:
                updated_task = Task(
                    task_id=existing_task.task_id,
                    story_id=existing_task.story_id,
                    title=existing_task.title,
                    created_at=existing_task.created_at,
                    updated_at=datetime.now(UTC),
                    plan_id=plan_id,
                    description=existing_task.description,
                    estimated_hours=existing_task.estimated_hours,
                    assigned_to=existing_task.assigned_to,
                    type=existing_task.type,
                    status=existing_task.status,
                    priority=existing_task.priority,
                )
                await self.storage.save_task(updated_task)
                tasks_updated += 1

        if tasks_updated > 0:
            logger.info(
                f"Updated {tasks_updated} existing tasks with plan_id {plan_id.value}"
            )

        return tasks_updated

    async def _create_tasks_from_decisions(
        self, plan_preliminary: PlanPreliminary, story_id: StoryId, plan_id: PlanId
    ) -> int:
        """Create high-level tasks from task decisions.

        Args:
            plan_preliminary: Plan preliminary with task decisions
            story_id: Story ID for tasks
            plan_id: Plan ID to link tasks to

        Returns:
            Number of tasks created
        """
        if not plan_preliminary.task_decisions:
            return 0

        logger.info(
            f"Creating {len(plan_preliminary.task_decisions)} tasks "
            f"with semantic decision metadata for plan {plan_id.value}"
        )

        from planning.domain.value_objects.identifiers.task_id import TaskId
        from planning.domain.value_objects.statuses.task_status import TaskStatus
        from planning.domain.value_objects.statuses.task_type import TaskType

        tasks_created = 0
        for task_decision in plan_preliminary.task_decisions:
            task_id = TaskId(f"TSK-{uuid4()}")
            now = datetime.now(UTC)
            task = Task(
                task_id=task_id,
                story_id=story_id,
                title=task_decision.task_description,
                created_at=now,
                updated_at=now,
                plan_id=plan_id,
                description=task_decision.decision_reason,
                type=TaskType.BACKLOG_REVIEW_IDENTIFIED,
                status=TaskStatus.TODO,
                assigned_to="",
                estimated_hours=0,
                priority=task_decision.task_index + 1,
            )

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

        return tasks_created

    async def _check_and_auto_complete_ceremony(
        self, ceremony: BacklogReviewCeremony, ceremony_id: BacklogReviewCeremonyId
    ) -> BacklogReviewCeremony:
        """Check if ceremony should auto-complete and update if needed.

        Args:
            ceremony: BacklogReviewCeremony to check
            ceremony_id: Ceremony ID for logging

        Returns:
            Updated ceremony (completed if conditions met, otherwise unchanged)
        """
        if not ceremony.status.is_reviewing():
            return ceremony

        # Check if all stories have tasks
        all_stories_have_tasks = True
        for story_id_check in ceremony.story_ids:
            tasks = await self.storage.list_tasks(
                story_id=story_id_check,
                limit=1,
                offset=0,
            )
            if not tasks:
                all_stories_have_tasks = False
                break

        # Check if all review_results are decided (not PENDING)
        all_reviews_decided = all(
            not result.approval_status.is_pending()
            for result in ceremony.review_results
        )

        if all_stories_have_tasks and all_reviews_decided:
            completed_at = datetime.now(UTC)
            ceremony = ceremony.complete(completed_at)
            logger.info(
                f"✅ Ceremony {ceremony_id.value} → COMPLETED (auto-complete: "
                f"all tasks created and all reviews decided)"
            )

        return ceremony

    async def _publish_plan_approved_event(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        plan_id: PlanId,
        approval: PlanApproval,
        approved_at: datetime,
        plan_preliminary: PlanPreliminary,
        tasks_created: int,
        tasks_updated: int,
    ) -> None:
        """Publish plan.approved event with PO context.

        Args:
            ceremony_id: Ceremony ID
            story_id: Story ID
            plan_id: Plan ID
            approval: Plan approval value object
            approved_at: Approval timestamp
            plan_preliminary: Plan preliminary for event data
            tasks_created: Number of tasks created
            tasks_updated: Number of tasks updated
        """
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
                    "tasks_updated": tasks_updated,
                    "po_notes": approval.po_notes,
                    "po_concerns": approval.po_concerns,
                    "priority_adjustment": approval.priority_adjustment,
                    "po_priority_reason": approval.po_priority_reason,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to publish plan.approved event: {e}")

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
        review_result = self._find_review_result(ceremony, story_id)

        # Check if already approved (idempotency check)
        # The mapper now updates approval_status from Valkey PO approvals (source-of-truth)
        # So if PO approval exists in Valkey, approval_status will be APPROVED here
        if review_result.approval_status.is_approved():
            # If already approved, retrieve existing plan_id
            if review_result.plan_id:
                # Retrieve existing plan
                existing_plan = await self.storage.get_plan(review_result.plan_id)
                if existing_plan:
                    logger.info(
                        f"Plan already approved for story {story_id.value} in ceremony {ceremony_id.value}. "
                        f"Returning existing plan: {review_result.plan_id.value}"
                    )
                    return existing_plan, ceremony
            else:
                # Status is APPROVED but no plan_id - prevent duplicate approval
                # This could happen if Neo4j hasn't been updated with plan_id yet
                # Raise error to prevent creating duplicate plans
                raise ValueError(
                    f"Review result for story {story_id.value} in ceremony {ceremony_id.value} "
                    f"is already APPROVED (PO approval found in Valkey), but no plan_id found in Neo4j. "
                    f"This may indicate Neo4j synchronization delay. "
                    f"Please wait for reconciliation or check Neo4j status."
                )

        # Generate plan_id BEFORE approving (so it can be included in approved_result)
        plan_preliminary = review_result.plan_preliminary
        plan_id = PlanId(f"PL-{uuid4()}")

        # Approve review result with PO context (immutably)
        approved_at = datetime.now(UTC)
        approved_result = review_result.approve(
            approved_by=approval.approved_by,
            approved_at=approved_at,
            po_notes=approval.po_notes,
            po_concerns=approval.po_concerns,
            priority_adjustment=approval.priority_adjustment,
            po_priority_reason=approval.po_priority_reason,
            plan_id=plan_id,
        )

        # Convert PlanPreliminary → Plan (official entity)
        plan = Plan(
            plan_id=plan_id,
            story_ids=(story_id,),
            title=plan_preliminary.title,
            description=plan_preliminary.description,
            acceptance_criteria=plan_preliminary.acceptance_criteria,
            technical_notes=plan_preliminary.technical_notes,
            roles=plan_preliminary.roles,
        )

        # Save Plan (persists to both Neo4j and Valkey)
        await self.storage.save_plan(plan)
        logger.info(f"Plan {plan_id.value} saved to storage (Neo4j + Valkey)")

        # Update existing tasks with plan_id
        tasks_updated = await self._update_existing_tasks_with_plan_id(story_id, plan_id)

        # Create high-level tasks from decisions
        tasks_created = await self._create_tasks_from_decisions(
            plan_preliminary, story_id, plan_id
        )

        # Update ceremony with approved result
        ceremony = ceremony.update_review_result(story_id, approved_result, approved_at)

        # Check if ceremony should auto-complete
        ceremony = await self._check_and_auto_complete_ceremony(ceremony, ceremony_id)

        # Persist ceremony
        await self.storage.save_backlog_review_ceremony(ceremony)

        logger.info(
            f"Approved plan {plan_id.value} for story {story_id.value} "
            f"by {approval.approved_by.value} with PO notes: {approval.po_notes[:50]}..."
        )

        # Publish event with PO context
        await self._publish_plan_approved_event(
            ceremony_id,
            story_id,
            plan_id,
            approval,
            approved_at,
            plan_preliminary,
            tasks_created,
            tasks_updated,
        )

        return plan, ceremony

