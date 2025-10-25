"""Port for connection management (technology-agnostic)."""
from abc import ABC, abstractmethod


class ConnectionPort(ABC):
    """Abstract port for connection operations."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to service.
        
        Raises:
            ConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from service."""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if connected.
        
        Returns:
            True if connected, False otherwise
        """
        pass
    
    @abstractmethod
    def get_stream_context(self):
        """Get stream processing context.
        
        Returns:
            Stream context object
            
        Raises:
            RuntimeError: If not connected
        """
        pass
