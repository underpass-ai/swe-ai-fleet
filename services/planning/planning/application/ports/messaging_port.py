"""Messaging port for Publishing domain events."""

from typing import Protocol, Any


class MessagingPort(Protocol):
    """
    Port (interface) for publishing domain events to NATS.
    
    Events Published:
    - story.created
    - story.transitioned
    - story.updated
    - decision.approved
    - decision.rejected
    """
    
    async def publish_event(
        self,
        subject: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Publish a domain event to NATS.
        
        Args:
            subject: NATS subject (e.g., "story.created").
            payload: Event payload (must be JSON-serializable).
        
        Raises:
            MessagingError: If publishing fails.
        """
        ...
    
    async def publish_story_created(
        self,
        story_id: str,
        title: str,
        created_by: str,
    ) -> None:
        """
        Publish story.created event.
        
        Args:
            story_id: ID of created story.
            title: Story title.
            created_by: User who created the story.
        
        Raises:
            MessagingError: If publishing fails.
        """
        ...
    
    async def publish_story_transitioned(
        self,
        story_id: str,
        from_state: str,
        to_state: str,
        transitioned_by: str,
    ) -> None:
        """
        Publish story.transitioned event.
        
        Args:
            story_id: ID of story.
            from_state: Previous state.
            to_state: New state.
            transitioned_by: User who triggered transition.
        
        Raises:
            MessagingError: If publishing fails.
        """
        ...
    
    async def publish_decision_approved(
        self,
        story_id: str,
        decision_id: str,
        approved_by: str,
        comment: str | None = None,
    ) -> None:
        """
        Publish decision.approved event.
        
        Args:
            story_id: ID of story.
            decision_id: ID of decision.
            approved_by: User who approved.
            comment: Optional approval comment.
        
        Raises:
            MessagingError: If publishing fails.
        """
        ...
    
    async def publish_decision_rejected(
        self,
        story_id: str,
        decision_id: str,
        rejected_by: str,
        reason: str,
    ) -> None:
        """
        Publish decision.rejected event.
        
        Args:
            story_id: ID of story.
            decision_id: ID of decision.
            rejected_by: User who rejected.
            reason: Rejection reason.
        
        Raises:
            MessagingError: If publishing fails.
        """
        ...

