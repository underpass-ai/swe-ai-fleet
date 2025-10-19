"""Task failed event entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain_event import DomainEvent


@dataclass(frozen=True)
class TaskFailedEvent(DomainEvent):
    """Event published when an agent fails to complete a task.
    
    This event is emitted when an agent encounters an error or fails to
    complete its assigned task within constraints.
    
    Attributes:
        task_id: Task identifier
        story_id: Story identifier
        agent_id: Agent identifier
        role: Agent role
        error: Error message
        error_type: Type of error (e.g., "TIMEOUT", "VALIDATION")
        timestamp: When the failure occurred
    """
    
    task_id: str
    story_id: str
    agent_id: str
    role: str
    error: str
    error_type: str
    timestamp: str
    
    @property
    def event_type(self) -> str:
        """Get event type identifier."""
        return "orchestration.task.failed"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of the event
        """
        return {
            "event_type": self.event_type,
            "task_id": self.task_id,
            "story_id": self.story_id,
            "agent_id": self.agent_id,
            "role": self.role,
            "error": self.error,
            "error_type": self.error_type,
            "timestamp": self.timestamp,
        }

