"""Durable Consumer Entity.

Represents a NATS JetStream durable consumer configuration.
Extracted from nats_source.py subscribe_to_stream() consumer setup.
"""

from dataclasses import dataclass


@dataclass
class DurableConsumer:
    """NATS Durable Consumer Configuration Entity.
    
    Represents a durable consumer for subscribing to NATS streams.
    A durable consumer maintains its state across reconnections.
    
    Extracted from nats_source.py lines 145-147:
    - subject or f"{stream_name}.>"
    - stream=stream_name
    - durable="monitoring-dashboard"
    
    Attributes:
        subject: Subject filter for the consumer
        stream_name: Name of the stream being consumed
        durable_name: Name for the durable consumer (persists state)
    """
    
    subject: str
    stream_name: str
    durable_name: str
    
    def validate(self) -> bool:
        """Validate consumer configuration.
        
        Returns:
            True if valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        if not self.subject or len(self.subject.strip()) == 0:
            raise ValueError("subject cannot be empty")
        if not self.stream_name or len(self.stream_name.strip()) == 0:
            raise ValueError("stream_name cannot be empty")
        if not self.durable_name or len(self.durable_name.strip()) == 0:
            raise ValueError("durable_name cannot be empty")
        return True
    
    def get_subject_filter(self) -> str:
        """Get subject filter.
        
        Returns:
            Subject filter string
        """
        return self.subject
    
    def get_consumer_name(self) -> str:
        """Get durable consumer name.
        
        Returns:
            Durable consumer name
        """
        return self.durable_name
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "subject": self.subject,
            "stream_name": self.stream_name,
            "durable_name": self.durable_name,
        }
    
    @classmethod
    def create(
        cls,
        subject: str,
        stream_name: str,
        durable_name: str,
    ) -> "DurableConsumer":
        """Factory method to create DurableConsumer with validation.
        
        Args:
            subject: Subject filter for consumer
            stream_name: Stream name
            durable_name: Durable consumer name
            
        Returns:
            DurableConsumer instance
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not subject or len(subject.strip()) == 0:
            raise ValueError("subject cannot be empty")
        if not stream_name or len(stream_name.strip()) == 0:
            raise ValueError("stream_name cannot be empty")
        if not durable_name or len(durable_name.strip()) == 0:
            raise ValueError("durable_name cannot be empty")
        
        return cls(
            subject=subject,
            stream_name=stream_name,
            durable_name=durable_name,
        )
    
    @classmethod
    def for_monitoring(
        cls,
        stream_name: str,
        subject: str | None = None,
    ) -> "DurableConsumer":
        """Create a monitoring durable consumer.
        
        Factory method for creating monitoring dashboard consumers.
        
        Args:
            stream_name: Stream to monitor
            subject: Optional subject filter
            
        Returns:
            DurableConsumer configured for monitoring
            
        Raises:
            ValueError: If parameters are invalid
        """
        subject_filter = subject or f"{stream_name}.>"
        consumer_name = "monitoring-dashboard"
        
        return cls.create(
            subject=subject_filter,
            stream_name=stream_name,
            durable_name=consumer_name,
        )
