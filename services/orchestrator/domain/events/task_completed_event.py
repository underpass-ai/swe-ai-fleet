"""Task completed event entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain_event import DomainEvent


@dataclass(frozen=True)
class TaskCompletedEvent(DomainEvent):
    """Event published when an agent completes a task.
    
    This event is emitted when an agent successfully completes its assigned
    task, including the results of any quality checks.
    
    Attributes:
        task_id: Task identifier
        story_id: Story identifier
        agent_id: Agent identifier
        role: Agent role
        duration_ms: Task execution duration in milliseconds
        checks_passed: Whether quality checks passed
        timestamp: When the task completed
    """
    
    task_id: str
    story_id: str
    agent_id: str
    role: str
    duration_ms: int
    checks_passed: bool
    timestamp: str
    
    @property
    def event_type(self) -> str:
        """Get event type identifier."""
        return "orchestration.task.completed"
    
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
            "duration_ms": self.duration_ms,
            "checks_passed": self.checks_passed,
            "timestamp": self.timestamp,
        }

