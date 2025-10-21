"""Plan approved event entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain_event import DomainEvent


@dataclass(frozen=True)
class PlanApprovedEvent(DomainEvent):
    """Event published when a plan is approved.
    
    This event indicates that a story plan has been approved and is ready
    for agent execution across the specified roles.
    
    Attributes:
        story_id: Story identifier
        plan_id: Plan identifier
        approved_by: Who approved the plan
        roles: List of roles needed for execution
        timestamp: When the plan was approved
    """
    
    story_id: str
    plan_id: str
    approved_by: str
    roles: list[str]
    timestamp: str
    
    @property
    def event_type(self) -> str:
        """Get event type identifier."""
        return "orchestration.plan.approved"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of the event
        """
        return {
            "event_type": self.event_type,
            "story_id": self.story_id,
            "plan_id": self.plan_id,
            "approved_by": self.approved_by,
            "roles": self.roles,
            "timestamp": self.timestamp,
        }

