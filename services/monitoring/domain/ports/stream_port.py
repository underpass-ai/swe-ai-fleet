"""Port for stream operations (technology-agnostic)."""
from abc import ABC, abstractmethod


class StreamPort(ABC):
    """Abstract port for stream operations."""
    
    @abstractmethod
    def set_context(self, stream_context) -> None:
        """Set stream processing context.
        
        Args:
            stream_context: Stream context from connection
        """
        pass
    
    @abstractmethod
    async def pull_subscribe(self, subject: str, stream: str, durable: str | None = None):
        """Create a pull subscription.
        
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
        """Create a push subscription.
        
        Args:
            subject: Subject filter
            stream: Optional stream name
            ordered_consumer: Whether to use ordered consumer
            
        Returns:
            Consumer subscription object
        """
        pass
