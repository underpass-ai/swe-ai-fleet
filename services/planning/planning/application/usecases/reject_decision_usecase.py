"""Reject Decision use case."""

from dataclasses import dataclass

from planning.application.ports import MessagingPort
from planning.domain import StoryId


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
        decision_id: str,
        rejected_by: str,
        reason: str,
    ) -> None:
        """
        Reject a decision.

        Args:
            story_id: ID of story.
            decision_id: ID of decision to reject.
            rejected_by: User (PO) who rejected.
            reason: Rejection reason (required).

        Raises:
            ValueError: If inputs are invalid.
            MessagingError: If event publishing fails.
        """
        # Validate inputs
        if not decision_id or not decision_id.strip():
            raise ValueError("decision_id cannot be empty")

        if not rejected_by or not rejected_by.strip():
            raise ValueError("rejected_by cannot be empty")

        if not reason or not reason.strip():
            raise ValueError("rejection reason cannot be empty")

        # Publish decision.rejected event
        # Orchestrator will listen and trigger re-deliberation
        await self.messaging.publish_decision_rejected(
            story_id=story_id.value,
            decision_id=decision_id.strip(),
            rejected_by=rejected_by.strip(),
            reason=reason.strip(),
        )

