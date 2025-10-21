"""Decision added event entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DecisionAddedEvent:
    """Event received when a decision is added to context.
    
    Origin: Context Service
    Subject: context.decision.added
    
    Attributes:
        story_id: Story identifier
        decision_id: Decision identifier
        decision_type: Type of decision (default: TECHNICAL)
    """
    
    story_id: str
    decision_id: str
    decision_type: str = "TECHNICAL"
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecisionAddedEvent:
        """Create event from dictionary.
        
        Args:
            data: Event data from NATS message
            
        Returns:
            DecisionAddedEvent instance
            
        Raises:
            ValueError: If required fields missing
        """
        required = ["story_id", "decision_id"]
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        
        return cls(
            story_id=data["story_id"],
            decision_id=data["decision_id"],
            decision_type=data.get("decision_type", "TECHNICAL"),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "story_id": self.story_id,
            "decision_id": self.decision_id,
            "decision_type": self.decision_type,
        }

