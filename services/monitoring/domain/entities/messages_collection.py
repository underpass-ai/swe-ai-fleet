"""Messages Collection Entity.

Represents a collection of NATS stream messages.
"""

from dataclasses import dataclass, field
from typing import Sequence

from .stream_message import StreamMessage


@dataclass
class MessagesCollection:
    """Collection of Stream Messages.
    
    Aggregate root representing multiple messages from a stream.
    Provides query and filtering capabilities on the message set.
    
    Attributes:
        messages: Sequence of StreamMessage objects
    """
    
    messages: Sequence[StreamMessage] = field(default_factory=list)
    
    def count(self) -> int:
        """Get total number of messages in collection.
        
        Returns:
            Number of messages
        """
        return len(self.messages)
    
    def is_empty(self) -> bool:
        """Check if collection is empty.
        
        Returns:
            True if no messages
        """
        return self.count() == 0
    
    def get_latest(self) -> StreamMessage | None:
        """Get the most recent message (highest sequence).
        
        Returns:
            Latest message or None if collection is empty
        """
        if self.is_empty():
            return None
        return max(self.messages, key=lambda m: m.sequence)
    
    def get_oldest(self) -> StreamMessage | None:
        """Get the oldest message (lowest sequence).
        
        Returns:
            Oldest message or None if collection is empty
        """
        if self.is_empty():
            return None
        return min(self.messages, key=lambda m: m.sequence)
    
    def filter_by_subject(self, subject: str) -> "MessagesCollection":
        """Filter messages by subject.
        
        Args:
            subject: Subject to filter by
            
        Returns:
            New MessagesCollection with filtered messages
        """
        filtered = [m for m in self.messages if m.subject == subject]
        return MessagesCollection(messages=filtered)
    
    def filter_by_event_type(self, event_type: str) -> "MessagesCollection":
        """Filter messages by event type.
        
        Args:
            event_type: Event type to filter by
            
        Returns:
            New MessagesCollection with filtered messages
        """
        filtered = [
            m for m in self.messages
            if m.get_event_type() == event_type
        ]
        return MessagesCollection(messages=filtered)
    
    def get_sequence_range(self) -> tuple[int, int] | None:
        """Get min and max sequence numbers.
        
        Returns:
            Tuple of (min_seq, max_seq) or None if empty
        """
        if self.is_empty():
            return None
        sequences = [m.sequence for m in self.messages]
        return (min(sequences), max(sequences))
    
    def to_list(self) -> list[dict]:
        """Convert collection to list of dictionaries.
        
        Returns:
            List of message dictionaries
        """
        return [msg.to_dict() for msg in self.messages]
