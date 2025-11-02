"""Approve Decision use case."""

from dataclasses import dataclass

from planning.application.ports import MessagingPort
from planning.domain import StoryId


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
        decision_id: str,
        approved_by: str,
        comment: str | None = None,
    ) -> None:
        """
        Approve a decision.
        
        Args:
            story_id: ID of story.
            decision_id: ID of decision to approve.
            approved_by: User (PO) who approved.
            comment: Optional approval comment.
        
        Raises:
            ValueError: If inputs are invalid.
            MessagingError: If event publishing fails.
        """
        # Validate inputs
        if not decision_id or not decision_id.strip():
            raise ValueError("decision_id cannot be empty")
        
        if not approved_by or not approved_by.strip():
            raise ValueError("approved_by cannot be empty")
        
        # Publish decision.approved event
        # Orchestrator will listen and trigger execution
        await self.messaging.publish_decision_approved(
            story_id=story_id.value,
            decision_id=decision_id.strip(),
            approved_by=approved_by.strip(),
            comment=comment.strip() if comment else None,
        )

