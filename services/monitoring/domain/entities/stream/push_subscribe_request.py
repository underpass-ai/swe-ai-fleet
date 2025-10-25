"""Push subscribe request configuration."""
from dataclasses import dataclass


@dataclass
class PushSubscribeRequest:
    """
    Configuration for push subscribe operations.
    
    Encapsulates parameters for StreamPort.subscribe().
    """
    
    subject: str
    stream: str | None = None
    ordered_consumer: bool = False
    
    def validate(self) -> None:
        """Validate push subscribe request parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        if not self.subject or len(self.subject.strip()) == 0:
            raise ValueError("subject cannot be empty")
        if self.stream is not None and len(self.stream.strip()) == 0:
            raise ValueError("stream cannot be empty string")
        if not isinstance(self.ordered_consumer, bool):
            raise ValueError("ordered_consumer must be boolean")
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation.
        
        Returns:
            Dict with push subscribe configuration
        """
        result = {
            "subject": self.subject,
            "ordered_consumer": self.ordered_consumer,
        }
        if self.stream:
            result["stream"] = self.stream
        return result
    
    @classmethod
    def create(
        cls,
        subject: str,
        stream: str | None = None,
        ordered_consumer: bool = False,
    ) -> "PushSubscribeRequest":
        """Factory method to create validated PushSubscribeRequest.
        
        Args:
            subject: Subject filter
            stream: Optional stream name
            ordered_consumer: Whether to use ordered consumer
            
        Returns:
            PushSubscribeRequest instance
            
        Raises:
            ValueError: If validation fails
        """
        instance = cls(subject=subject, stream=stream, ordered_consumer=ordered_consumer)
        instance.validate()
        return instance
