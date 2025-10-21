"""Phase changed event entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain_event import DomainEvent


@dataclass(frozen=True)
class PhaseChangedEvent(DomainEvent):
    """Event published when a story transitions between phases.
    
    This event is published when a story moves from one development phase
    to another (e.g., DESIGN → BUILD → TEST).
    
    Attributes:
        story_id: Story identifier
        from_phase: Previous phase (e.g., "DESIGN")
        to_phase: New phase (e.g., "BUILD")
        timestamp: When the phase change occurred
    """
    
    story_id: str
    from_phase: str
    to_phase: str
    timestamp: str
    
    @property
    def event_type(self) -> str:
        """Get event type identifier."""
        return "orchestration.phase.changed"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of the event
        """
        return {
            "event_type": self.event_type,
            "story_id": self.story_id,
            "from_phase": self.from_phase,
            "to_phase": self.to_phase,
            "timestamp": self.timestamp,
        }

