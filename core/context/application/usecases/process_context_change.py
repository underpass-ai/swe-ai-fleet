"""Unified use case to process context changes from agents.

This is a Command Handler following CQRS pattern.
"""

import json
import logging

from core.context.application.usecases.record_milestone import RecordMilestoneUseCase
from core.context.usecases.project_decision import ProjectDecisionUseCase
from core.context.usecases.project_plan_version import ProjectPlanVersionUseCase
from core.context.usecases.project_story import ProjectStoryUseCase
from core.context.usecases.project_task import ProjectTaskUseCase

logger = logging.getLogger(__name__)


class ProcessContextChangeUseCase:
    """Process context changes from agent execution.

    Command Handler (CQRS pattern) that routes entity changes to
    appropriate use cases based on entity type.

    Responsibility:
    - Route changes to correct use case
    - Handle different entity types (DECISION, SUBTASK, CASE, PLAN, MILESTONE)
    - Provide consistent error handling

    Following Hexagonal Architecture + DDD.
    """

    def __init__(
        self,
        decision_uc: ProjectDecisionUseCase,
        task_uc: ProjectTaskUseCase,
        story_uc: ProjectStoryUseCase,
        plan_uc: ProjectPlanVersionUseCase,
        milestone_uc: RecordMilestoneUseCase,
    ):
        """Initialize with all required use cases (DI).

        Args:
            decision_uc: Use case for decision operations
            task_uc: Use case for task/subtask operations
            story_uc: Use case for story/case operations
            plan_uc: Use case for plan operations
            milestone_uc: Use case for milestone operations
        """
        self._decision_uc = decision_uc
        self._task_uc = task_uc
        self._story_uc = story_uc
        self._plan_uc = plan_uc
        self._milestone_uc = milestone_uc

    async def execute(
        self,
        change,
        story_id: str,
    ) -> None:
        """Execute context change processing.

        Routes to appropriate use case based on entity_type.

        Args:
            change: ContextChange protobuf message with operation, entity_type, entity_id, payload
            story_id: Parent story ID

        Raises:
            ValueError: If invalid entity_type or missing required fields
            Exception: If use case execution fails
        """
        # Validate required fields
        if not change.operation or not change.entity_type or not change.entity_id:
            raise ValueError("Missing required fields in context change")

        logger.info(
            f"Processing context change: story={story_id}, "
            f"operation={change.operation}, entity={change.entity_type}/{change.entity_id}",
            extra={
                "story_id": story_id,
                "entity_type": change.entity_type,
                "entity_id": change.entity_id,
                "operation": change.operation,
                "use_case": "ProcessContextChange",
            },
        )

        # Parse payload
        payload_data = {}
        if change.payload:
            try:
                payload_data = json.loads(change.payload)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON payload: {e}")
                raise ValueError(f"Invalid JSON payload: {e}")

        # Route to appropriate use case
        if change.entity_type == "DECISION":
            await self._handle_decision_change(story_id, change, payload_data)
        elif change.entity_type == "SUBTASK":
            await self._handle_subtask_change(story_id, change, payload_data)
        elif change.entity_type == "MILESTONE":
            await self._handle_milestone_change(story_id, change, payload_data)
        elif change.entity_type == "CASE":
            await self._handle_case_change(change, payload_data)
        elif change.entity_type == "PLAN":
            await self._handle_plan_change(story_id, change, payload_data)
        else:
            raise ValueError(f"Unknown entity type: {change.entity_type}")

        logger.info(f"✓ Context change processed: {change.entity_id}")

    async def _handle_decision_change(self, story_id: str, change, payload: dict) -> None:
        """Handle DECISION entity changes."""
        # Use ProjectDecisionUseCase (already accepts dict payload)
        use_case_payload = {
            "node_id": change.entity_id,
            "case_id": story_id,
            **payload,
        }
        await self._decision_uc.execute(use_case_payload)

    async def _handle_subtask_change(self, story_id: str, change, payload: dict) -> None:
        """Handle SUBTASK entity changes."""
        # Both CREATE and UPDATE operations use the same logic
        use_case_payload = {
            "sub_id": change.entity_id,
            "plan_id": story_id,
            **payload,
        }
        await self._task_uc.execute(use_case_payload)

    async def _handle_milestone_change(self, story_id: str, change, payload: dict) -> None:
        """Handle MILESTONE entity changes."""
        import time
        await self._milestone_uc.execute(
            milestone_id=change.entity_id,
            story_id=story_id,
            event_type=payload.get("event_type", "milestone"),
            description=payload.get("description", ""),
            timestamp_ms=int(time.time() * 1000),
        )

    async def _handle_case_change(self, change, payload: dict) -> None:
        """Handle CASE entity changes."""
        use_case_payload = {
            "case_id": change.entity_id,
            **payload,
        }
        await self._story_uc.execute(use_case_payload)

    async def _handle_plan_change(self, story_id: str, change, payload: dict) -> None:
        """Handle PLAN entity changes."""
        use_case_payload = {
            "plan_id": change.entity_id,
            "case_id": story_id,
            **payload,
        }
        await self._plan_uc.execute(use_case_payload)

