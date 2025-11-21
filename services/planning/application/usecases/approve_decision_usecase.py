"""Approve Decision use case."""

from dataclasses import dataclass

from planning.application.ports import MessagingPort
from planning.domain import Comment, DecisionId, StoryId, UserName


@dataclass
class ApproveDecisionUseCase:
    """
    Use Case: Approve a decision for a story.

    Business Rules:
    - Decision approval triggers orchestrator execution
    - PO must provide approval
    - Optional comment can be added

    Dependencies:
    - MessagingPort: Publish decision.approved event

    Note: Decision entities are managed by Context Service.
    This use case only handles the approval workflow.
    """

    messaging: MessagingPort

    async def execute(
        self,
        story_id: StoryId,
        decision_id: DecisionId,
        approved_by: UserName,
        comment: Comment | None = None,
    ) -> None:
        """
        Approve a decision.

        Args:
            story_id: Domain StoryId value object.
            decision_id: Domain DecisionId value object.
            approved_by: Domain UserName value object.
            comment: Optional Comment value object.

        Raises:
            ValueError: If inputs are invalid.
            MessagingError: If event publishing fails.
        """
        # Validation already done by Value Objects' __post_init__

        # Publish decision.approved event
        # Orchestrator will listen and trigger execution
        await self.messaging.publish_decision_approved(
            story_id=story_id,  # Pass Value Object directly
            decision_id=decision_id,  # Pass Value Object directly
            approved_by=approved_by,  # Pass Value Object directly
            comment=comment,  # Pass Value Object directly (or None)
        )

