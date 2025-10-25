"""Port for NATS connection management."""
from abc import ABC, abstractmethod


class NATSConnectionPort(ABC):
    """Abstract port for NATS connection operations."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to NATS server.
        
        Raises:
            ConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from NATS server."""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if connected to NATS.
        
        Returns:
            True if connected, False otherwise
        """
        pass
    
    @abstractmethod
    def get_jetstream(self):
        """Get JetStream context for NATS operations.
        
        Returns:
            JetStream context object
            
        Raises:
            RuntimeError: If not connected
        """
        pass
