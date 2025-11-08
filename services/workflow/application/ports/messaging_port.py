"""Messaging port for event publishing.

Defines interface for publishing workflow events.
Following Hexagonal Architecture (Port).
"""

from typing import Protocol

from services.workflow.domain.entities.workflow_state import WorkflowState


class MessagingPort(Protocol):
    """Port for publishing workflow events.
    
    Defines interface for event-driven communication.
    Implemented by infrastructure adapters (NATS, Kafka, etc.).
    
    Following Hexagonal Architecture:
    - This is a PORT (interface)
    - Infrastructure provides ADAPTERS (NATS adapter)
    - Application depends on PORT, not concrete ADAPTER
    """
    
    async def publish_state_changed(
        self,
        workflow_state: WorkflowState,
        event_type: str,
    ) -> None:
        """Publish workflow state changed event.
        
        Args:
            workflow_state: New workflow state
            event_type: Event type (state_changed, task_assigned, etc.)
        """
        ...
    
    async def publish_task_assigned(
        self,
        task_id: str,
        story_id: str,
        role: str,
        action_required: str,
    ) -> None:
        """Publish task assigned event.
        
        Notifies that a task is ready for a specific role to act.
        
        Args:
            task_id: Task identifier
            story_id: Story identifier
            role: Role that should act
            action_required: Action that should be performed
        """
        ...
    
    async def publish_validation_required(
        self,
        task_id: str,
        story_id: str,
        validator_role: str,
        artifact_type: str,
    ) -> None:
        """Publish validation required event.
        
        Notifies validators (Architect, QA, PO) that work is ready for review.
        
        Args:
            task_id: Task identifier
            story_id: Story identifier
            validator_role: Role that should validate (architect, qa, po)
            artifact_type: What to validate (design, tests, story)
        """
        ...
    
    async def publish_task_completed(
        self,
        task_id: str,
        story_id: str,
        final_state: str,
    ) -> None:
        """Publish task completed event.
        
        Notifies that a task reached a terminal state (done, cancelled).
        
        Args:
            task_id: Task identifier
            story_id: Story identifier
            final_state: Terminal state (done, cancelled)
        """
        ...

