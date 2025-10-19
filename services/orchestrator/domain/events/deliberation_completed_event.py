"""Deliberation completed event entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain_event import DomainEvent


@dataclass(frozen=True)
class DeliberationCompletedEvent(DomainEvent):
    """Event published when a deliberation is completed.
    
    This event is emitted when all agents in a council have completed their
    deliberation and decisions have been made.
    
    Attributes:
        story_id: Story identifier
        task_id: Task identifier
        decisions: List of decisions made
        timestamp: When the deliberation completed
    """
    
    story_id: str
    task_id: str
    decisions: list[dict[str, Any]]
    timestamp: float
    
    @property
    def event_type(self) -> str:
        """Get event type identifier."""
        return "orchestration.deliberation.completed"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of the event
        """
        return {
            "event_type": self.event_type,
            "story_id": self.story_id,
            "task_id": self.task_id,
            "decisions": self.decisions,
            "timestamp": self.timestamp,
        }

