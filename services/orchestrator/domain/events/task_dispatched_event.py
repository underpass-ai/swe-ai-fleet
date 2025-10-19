"""Task dispatched event entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain_event import DomainEvent


@dataclass(frozen=True)
class TaskDispatchedEvent(DomainEvent):
    """Event published when a task is dispatched to an agent.
    
    This event indicates that a task has been assigned to a specific agent
    and is waiting for execution.
    
    Attributes:
        story_id: Story identifier
        task_id: Task identifier
        agent_id: Agent identifier
        role: Agent role
        timestamp: When the task was dispatched
    """
    
    story_id: str
    task_id: str
    agent_id: str
    role: str
    timestamp: str
    
    @property
    def event_type(self) -> str:
        """Get event type identifier."""
        return "orchestration.task.dispatched"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of the event
        """
        return {
            "event_type": self.event_type,
            "story_id": self.story_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "role": self.role,
            "timestamp": self.timestamp,
        }

