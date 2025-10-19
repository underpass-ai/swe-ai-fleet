"""Domain entities for incoming events from external services.

These entities represent events consumed from NATS that originate
from other microservices (Planning Service).

Following DDD principles:
- Strong typing for external event data
- Validation in constructors
- Immutable data structures
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StoryTransitionedEvent:
    """Event received when a story transitions between phases.
    
    Origin: Planning Service
    Subject: planning.story.transitioned
    
    Attributes:
        story_id: Story identifier
        from_phase: Previous phase
        to_phase: New phase
        timestamp: Event timestamp (ISO format)
    """
    
    story_id: str
    from_phase: str
    to_phase: str
    timestamp: str
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoryTransitionedEvent:
        """Create event from dictionary.
        
        Args:
            data: Event data from NATS message
            
        Returns:
            StoryTransitionedEvent instance
            
        Raises:
            ValueError: If required fields missing
        """
        required = ["story_id", "from_phase", "to_phase", "timestamp"]
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        
        return cls(
            story_id=data["story_id"],
            from_phase=data["from_phase"],
            to_phase=data["to_phase"],
            timestamp=data["timestamp"],
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for publishing.
        
        Returns:
            Dictionary representation
        """
        return {
            "story_id": self.story_id,
            "from_phase": self.from_phase,
            "to_phase": self.to_phase,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class PlanApprovedEvent:
    """Event received when a plan is approved.
    
    Origin: Planning Service
    Subject: planning.plan.approved
    
    Attributes:
        story_id: Story identifier
        plan_id: Plan identifier
        approved_by: Approver identifier
        roles: List of roles required
        timestamp: Event timestamp (ISO format)
    """
    
    story_id: str
    plan_id: str
    approved_by: str
    roles: list[str]
    timestamp: str
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlanApprovedEvent:
        """Create event from dictionary.
        
        Args:
            data: Event data from NATS message
            
        Returns:
            PlanApprovedEvent instance
            
        Raises:
            ValueError: If required fields missing
        """
        required = ["story_id", "plan_id", "approved_by", "timestamp"]
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        
        return cls(
            story_id=data["story_id"],
            plan_id=data["plan_id"],
            approved_by=data["approved_by"],
            roles=data.get("roles", []),
            timestamp=data["timestamp"],
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for publishing.
        
        Returns:
            Dictionary representation
        """
        return {
            "story_id": self.story_id,
            "plan_id": self.plan_id,
            "approved_by": self.approved_by,
            "roles": self.roles,
            "timestamp": self.timestamp,
        }

