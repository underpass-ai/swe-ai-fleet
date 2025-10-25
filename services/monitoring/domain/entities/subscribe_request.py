"""Subscribe Request Entity.

Represents parameters for subscribing to a NATS stream.
Extracted from nats_source.py subscribe_to_stream() parameters.
"""

from dataclasses import dataclass


@dataclass
class SubscribeRequest:
    """Stream Subscription Request Entity.
    
    Encapsulates parameters for subscribing to a NATS stream.
    Extracted from nats_source.py subscribe_to_stream() (lines 126-127).
    
    Attributes:
        stream_name: Name of the stream to subscribe to
        subject: Optional subject filter within the stream
    """
    
    stream_name: str
    subject: str | None = None
    
    def __post_init__(self):
        """Validate subscription request parameters on construction."""
        if not self.stream_name or len(self.stream_name.strip()) == 0:
            raise ValueError("stream_name cannot be empty")
    
    def validate(self) -> bool:
        """Validate subscription request parameters (already done in __post_init__).
        
        Returns:
            True if valid
        """
        return True
    
    def get_subject_filter(self) -> str:
        """Get subject filter for subscription.
        
        Returns:
            Subject filter, or wildcard if not specified
        """
        return self.subject or f"{self.stream_name}.>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "stream_name": self.stream_name,
            "subject": self.subject,
        }
    
    @classmethod
    def create(
        cls,
        stream_name: str,
        subject: str | None = None,
    ) -> "SubscribeRequest":
        """Factory method to create SubscribeRequest with validation.
        
        Args:
            stream_name: Name of stream to subscribe to
            subject: Optional subject filter
            
        Returns:
            SubscribeRequest instance
            
        Raises:
            ValueError: If parameters are invalid
        """
        return cls(
            stream_name=stream_name,
            subject=subject,
        )
