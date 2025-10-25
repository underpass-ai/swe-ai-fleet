"""Port for JetStream operations."""
from abc import ABC, abstractmethod


class JetStreamPort(ABC):
    """Abstract port for JetStream operations."""
    
    @abstractmethod
    async def pull_subscribe(self, subject: str, stream: str, durable: str | None = None):
        """Create a pull subscribe consumer.
        
        Args:
            subject: Subject filter
            stream: Stream name
            durable: Optional durable consumer name
            
        Returns:
            Consumer subscription object
        """
        pass
    
    @abstractmethod
    async def subscribe(self, subject: str, stream: str | None = None, ordered_consumer: bool = False):
        """Create a push subscribe consumer.
        
        Args:
            subject: Subject filter
            stream: Optional stream name
            ordered_consumer: Whether to use ordered consumer
            
        Returns:
            Consumer subscription object
        """
        pass
