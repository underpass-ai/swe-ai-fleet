"""Reject Decision use case."""

from dataclasses import dataclass

from planning.application.ports import MessagingPort
from planning.domain import DecisionId, Reason, StoryId, UserName


@dataclass
class RejectDecisionUseCase:
    """
    Use Case: Reject a decision for a story.

    Business Rules:
    - Decision rejection triggers re-deliberation
    - PO must provide reason
    - Agents will propose alternative solutions

    Dependencies:
    - MessagingPort: Publish decision.rejected event

    Note: Decision entities are managed by Context Service.
    This use case only handles the rejection workflow.
    """

    messaging: MessagingPort

    async def execute(
        self,
        story_id: StoryId,
        decision_id: DecisionId,
        rejected_by: UserName,
        reason: Reason,
    ) -> None:
        """
        Reject a decision.

        Args:
            story_id: Domain StoryId value object.
            decision_id: Domain DecisionId value object.
            rejected_by: Domain UserName value object.
            reason: Domain Reason value object.

        Raises:
            ValueError: If inputs are invalid.
            MessagingError: If event publishing fails.
        """
        # Validation already done by Value Objects' __post_init__

        # Publish decision.rejected event
        # Orchestrator will listen and trigger re-deliberation
        await self.messaging.publish_decision_rejected(
            story_id=story_id,  # Pass Value Object directly
            decision_id=decision_id,  # Pass Value Object directly
            rejected_by=rejected_by,  # Pass Value Object directly
            reason=reason,  # Pass Value Object directly
        )

