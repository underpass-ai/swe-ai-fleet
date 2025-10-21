"""Context updated event entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ContextUpdatedEvent:
    """Event received when context is updated.
    
    Origin: Context Service
    Subject: context.updated
    
    Attributes:
        story_id: Story identifier
        version: Context version number
    """
    
    story_id: str
    version: int
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContextUpdatedEvent:
        """Create event from dictionary.
        
        Args:
            data: Event data from NATS message
            
        Returns:
            ContextUpdatedEvent instance
            
        Raises:
            ValueError: If required fields missing
        """
        required = ["story_id", "version"]
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        
        return cls(
            story_id=data["story_id"],
            version=data["version"],
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "story_id": self.story_id,
            "version": self.version,
        }

