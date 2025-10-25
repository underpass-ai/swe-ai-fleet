"""Stream Message Entity.

Represents a message retrieved from a NATS stream.
Extracted from nats_source.py get_latest_messages() return structure.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class StreamMessage:
    """NATS Stream Message Entity.
    
    Represents a single message retrieved from a NATS stream.
    Extracted from nats_source.py lines 106-111.
    
    Attributes:
        subject: NATS subject where message came from
        data: Message payload as dictionary
        sequence: Sequence number in stream
        timestamp: ISO format timestamp when message was published
    """
    
    subject: str
    data: dict[str, Any]
    sequence: int
    timestamp: str
    
    def __post_init__(self):
        """Validate message on construction."""
        if not self.subject or len(self.subject.strip()) == 0:
            raise ValueError("subject cannot be empty")
        if self.sequence < 0:
            raise ValueError("sequence cannot be negative")
        if not self.timestamp or len(self.timestamp.strip()) == 0:
            raise ValueError("timestamp cannot be empty")
        if self.data is None:
            raise ValueError("data cannot be None")
    
    def get_event_type(self) -> str | None:
        """Extract event type from message data.
        
        Returns:
            Event type if data contains 'type' field, None otherwise
        """
        return self.data.get("type")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "subject": self.subject,
            "data": self.data,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def create(
        cls,
        subject: str,
        data: dict[str, Any],
        sequence: int,
        timestamp: str,
    ) -> "StreamMessage":
        """Factory method to create StreamMessage with validation.
        
        Args:
            subject: NATS subject
            data: Message payload
            sequence: Sequence number
            timestamp: ISO format timestamp
            
        Returns:
            StreamMessage instance
            
        Raises:
            ValueError: If parameters are invalid
        """
        return cls(
            subject=subject,
            data=data,
            sequence=sequence,
            timestamp=timestamp,
        )
