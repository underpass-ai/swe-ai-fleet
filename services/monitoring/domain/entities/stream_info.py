"""Stream Information Entity.

Represents NATS JetStream stream as domain aggregate root.
Extracted from nats_source.py get_stream_info() return structure.
"""

from dataclasses import dataclass
from typing import Sequence


@dataclass
class StreamInfo:
    """NATS Stream Information Entity.
    
    Aggregate root representing a NATS JetStream stream.
    Contains all metadata about the stream's current state.
    
    Attributes:
        name: Stream name (e.g., "PLANNING_EVENTS")
        subjects: Subjects this stream subscribes to
        messages: Total number of messages in stream
        bytes: Total bytes stored in stream
        first_seq: Sequence number of first message
        last_seq: Sequence number of last message
        consumer_count: Number of active consumers
    """
    
    name: str
    subjects: Sequence[str]
    messages: int
    bytes: int
    first_seq: int
    last_seq: int
    consumer_count: int
    
    def is_empty(self) -> bool:
        """Check if stream has no messages."""
        return self.messages == 0
    
    def get_size_mb(self) -> float:
        """Get stream size in megabytes."""
        return self.bytes / (1024 * 1024)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "subjects": list(self.subjects),
            "messages": self.messages,
            "bytes": self.bytes,
            "first_seq": self.first_seq,
            "last_seq": self.last_seq,
            "consumer_count": self.consumer_count,
        }
    
    @classmethod
    def create(
        cls,
        name: str,
        subjects: Sequence[str],
        messages: int,
        bytes: int,
        first_seq: int,
        last_seq: int,
        consumer_count: int,
    ) -> "StreamInfo":
        """Factory method to create StreamInfo.
        
        Args:
            name: Stream name
            subjects: Stream subjects
            messages: Message count
            bytes: Total bytes
            first_seq: First sequence number
            last_seq: Last sequence number
            consumer_count: Number of consumers
            
        Returns:
            StreamInfo instance
        """
        return cls(
            name=name,
            subjects=subjects,
            messages=messages,
            bytes=bytes,
            first_seq=first_seq,
            last_seq=last_seq,
            consumer_count=consumer_count,
        )
