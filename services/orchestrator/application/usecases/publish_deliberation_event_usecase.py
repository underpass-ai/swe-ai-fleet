"""Use case for publishing deliberation completion/failure events."""

from __future__ import annotations

from typing import NamedTuple

from services.orchestrator.domain.entities import DeliberationStateRegistry
from services.orchestrator.domain.ports import MessagingPort


class DeliberationEventPublished(NamedTuple):
    """Result of publishing deliberation event.
    
    Attributes:
        task_id: Task identifier
        event_type: Type of event published ("completed" or "failed")
        published: Whether event was successfully published
    """
    
    task_id: str
    event_type: str
    published: bool


class PublishDeliberationCompletedUseCase:
    """Use case for publishing deliberation completed events.
    
    This use case encapsulates the business logic for finalizing
    a completed deliberation and publishing the event.
    
    Following Clean Architecture:
    - Coordinates domain entity and messaging port
    - Marks state as completed
    - Publishes event via MessagingPort
    """
    
    def __init__(
        self,
        registry: DeliberationStateRegistry,
        messaging: MessagingPort,
    ):
        """Initialize the use case.
        
        Args:
            registry: Deliberation state registry
            messaging: Port for publishing events
        """
        self._registry = registry
        self._messaging = messaging
    
    async def execute(self, task_id: str) -> DeliberationEventPublished:
        """Publish deliberation completed event.
        
        Args:
            task_id: Task identifier
            
        Returns:
            DeliberationEventPublished result
            
        Raises:
            RuntimeError: If state not found
        """
        state = self._registry.get_state(task_id)
        if not state:
            raise RuntimeError(f"Deliberation state not found: {task_id}")
        
        # Create result dict using domain method (Tell, Don't Ask)
        result = state.to_completed_result_dict()
        
        # Mark state as completed
        state.mark_completed(result)
        
        # Publish event via MessagingPort
        try:
            await self._messaging.publish_dict(
                subject="deliberation.completed",
                data=result,
            )
            return DeliberationEventPublished(
                task_id=task_id,
                event_type="completed",
                published=True,
            )
        except Exception:
            return DeliberationEventPublished(
                task_id=task_id,
                event_type="completed",
                published=False,
            )


class PublishDeliberationFailedUseCase:
    """Use case for publishing deliberation failed events.
    
    This use case encapsulates the business logic for finalizing
    a failed deliberation and publishing the event.
    
    Following Clean Architecture:
    - Coordinates domain entity and messaging port
    - Marks state as failed
    - Publishes event via MessagingPort
    """
    
    def __init__(
        self,
        registry: DeliberationStateRegistry,
        messaging: MessagingPort,
    ):
        """Initialize the use case.
        
        Args:
            registry: Deliberation state registry
            messaging: Port for publishing events
        """
        self._registry = registry
        self._messaging = messaging
    
    async def execute(
        self,
        task_id: str,
        error_message: str,
    ) -> DeliberationEventPublished:
        """Publish deliberation failed event.
        
        Args:
            task_id: Task identifier
            error_message: Error description
            
        Returns:
            DeliberationEventPublished result
            
        Raises:
            RuntimeError: If state not found
        """
        state = self._registry.get_state(task_id)
        if not state:
            raise RuntimeError(f"Deliberation state not found: {task_id}")
        
        # Create result dict using domain method (Tell, Don't Ask)
        result = state.to_failed_result_dict(error_message)
        
        # Mark state as failed
        state.mark_failed(error_message)
        
        # Publish event via MessagingPort
        try:
            await self._messaging.publish_dict(
                subject="deliberation.failed",
                data=result,
            )
            return DeliberationEventPublished(
                task_id=task_id,
                event_type="failed",
                published=True,
            )
        except Exception:
            return DeliberationEventPublished(
                task_id=task_id,
                event_type="failed",
                published=False,
            )

