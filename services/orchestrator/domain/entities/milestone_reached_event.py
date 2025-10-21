"""Milestone reached event entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MilestoneReachedEvent:
    """Event received when a milestone is reached.
    
    Origin: Context Service
    Subject: context.milestone.reached
    
    Attributes:
        story_id: Story identifier
        milestone_id: Milestone identifier
        milestone_name: Milestone name
    """
    
    story_id: str
    milestone_id: str
    milestone_name: str
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MilestoneReachedEvent:
        """Create event from dictionary.
        
        Args:
            data: Event data from NATS message
            
        Returns:
            MilestoneReachedEvent instance
            
        Raises:
            ValueError: If required fields missing
        """
        required = ["story_id", "milestone_id", "milestone_name"]
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        
        return cls(
            story_id=data["story_id"],
            milestone_id=data["milestone_id"],
            milestone_name=data["milestone_name"],
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "story_id": self.story_id,
            "milestone_id": self.milestone_id,
            "milestone_name": self.milestone_name,
        }

