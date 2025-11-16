"""Use case to record plan approval in graph (audit trail)."""

import logging

from core.context.domain.plan_approval import PlanApproval
from core.context.ports.graph_command_port import GraphCommandPort

logger = logging.getLogger(__name__)


class RecordPlanApprovalUseCase:
    """Record a plan approval in the graph for audit trail.

    Bounded Context: Context Service
    Trigger: planning.plan.approved event from Planning Service

    Responsibility:
    - Create PlanApproval entity
    - Persist via Port

    Following Hexagonal Architecture + DDD.
    """

    def __init__(self, graph_command: GraphCommandPort):
        """Initialize use case with dependency injection via Port."""
        self._graph = graph_command

    async def execute(self, approval: PlanApproval) -> None:
        """Execute plan approval recording.

        Args:
            approval: PlanApproval domain entity
        """
        # Tell, Don't Ask: entity provides its own log context
        log_ctx = approval.get_log_context()
        log_ctx["use_case"] = "RecordPlanApproval"

        logger.info(
            f"Recording plan approval: {approval.plan_id.to_string()} "
            f"for story {approval.story_id.to_string()}",
            extra=log_ctx,
        )

        # Persist via Port
        await self._graph.save_plan_approval(approval)

        logger.info(
            f"✓ Plan approval recorded: {approval.plan_id.to_string()}",
            extra=log_ctx,
        )

