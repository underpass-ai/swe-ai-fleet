"""Pull subscribe request configuration."""
from dataclasses import dataclass


@dataclass
class PullSubscribeRequest:
    """
    Configuration for pull subscribe operations.
    
    Encapsulates parameters for StreamPort.pull_subscribe().
    """
    
    subject: str
    stream: str
    durable: str | None = None
    
    def validate(self) -> None:
        """Validate pull subscribe request parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        if not self.subject or len(self.subject.strip()) == 0:
            raise ValueError("subject cannot be empty")
        if not self.stream or len(self.stream.strip()) == 0:
            raise ValueError("stream cannot be empty")
        if self.durable is not None and len(self.durable.strip()) == 0:
            raise ValueError("durable cannot be empty string")
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation.
        
        Returns:
            Dict with pull subscribe configuration
        """
        result = {
            "subject": self.subject,
            "stream": self.stream,
        }
        if self.durable:
            result["durable"] = self.durable
        return result
    
    @classmethod
    def create(
        cls,
        subject: str,
        stream: str,
        durable: str | None = None,
    ) -> "PullSubscribeRequest":
        """Factory method to create validated PullSubscribeRequest.
        
        Args:
            subject: Subject filter
            stream: Stream name
            durable: Optional durable consumer name
            
        Returns:
            PullSubscribeRequest instance
            
        Raises:
            ValueError: If validation fails
        """
        instance = cls(subject=subject, stream=stream, durable=durable)
        instance.validate()
        return instance
