"""Stream Query Entity.

Represents parameters for querying messages from a NATS stream.
Extracted from nats_source.py get_latest_messages() parameters.
"""

from dataclasses import dataclass


@dataclass
class StreamQuery:
    """Stream Message Query Entity.
    
    Encapsulates parameters for querying latest messages from a stream.
    Extracted from nats_source.py get_latest_messages() (lines 73-75).
    
    Attributes:
        stream_name: Name of the stream to query
        subject: Optional subject filter within the stream
        limit: Maximum number of messages to retrieve (default 10)
    """
    
    stream_name: str
    subject: str | None = None
    limit: int = 10
    
    def validate(self) -> bool:
        """Validate query parameters.
        
        Returns:
            True if valid
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not self.stream_name or len(self.stream_name.strip()) == 0:
            raise ValueError("stream_name cannot be empty")
        if self.limit <= 0:
            raise ValueError("limit must be greater than 0")
        if self.limit > 10000:
            raise ValueError("limit cannot exceed 10000")
        return True
    
    def get_subject_filter(self) -> str:
        """Get subject filter for query.
        
        Returns:
            Subject filter, or wildcard if not specified
        """
        return self.subject or f"{self.stream_name}.>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "stream_name": self.stream_name,
            "subject": self.subject,
            "limit": self.limit,
        }
    
    @classmethod
    def create(
        cls,
        stream_name: str,
        subject: str | None = None,
        limit: int = 10,
    ) -> "StreamQuery":
        """Factory method to create StreamQuery with validation.
        
        Args:
            stream_name: Name of stream to query
            subject: Optional subject filter
            limit: Max messages (default 10, max 10000)
            
        Returns:
            StreamQuery instance
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not stream_name or len(stream_name.strip()) == 0:
            raise ValueError("stream_name cannot be empty")
        if limit <= 0:
            raise ValueError("limit must be greater than 0")
        if limit > 10000:
            raise ValueError("limit cannot exceed 10000")
        
        return cls(
            stream_name=stream_name,
            subject=subject,
            limit=limit,
        )
