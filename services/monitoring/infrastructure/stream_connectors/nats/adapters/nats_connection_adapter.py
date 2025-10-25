"""NATS-specific connection adapter."""
import nats
import logging

from services.monitoring.domain.ports.connection_port import ConnectionPort

logger = logging.getLogger(__name__)


class NATSConnectionAdapter(ConnectionPort):
    """NATS implementation of ConnectionPort."""
    
    def __init__(self, nats_url: str):
        """Initialize NATS connection adapter.
        
        Args:
            nats_url: NATS server URL (e.g., 'nats://localhost:4222')
        """
        self.nats_url = nats_url
        self.nc = None
        self.js = None
    
    async def connect(self) -> None:
        """Establish connection to NATS server.
        
        Raises:
            ConnectionError: If connection fails
        """
        try:
            self.nc = await nats.connect(self.nats_url)
            self.js = self.nc.jetstream()
            logger.info(f"Connected to NATS at {self.nats_url}")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise ConnectionError(f"Cannot connect to NATS at {self.nats_url}") from e
    
    async def disconnect(self) -> None:
        """Disconnect from NATS server."""
        if self.nc:
            await self.nc.close()
            self.nc = None
            self.js = None
            logger.info("Disconnected from NATS")
    
    async def is_connected(self) -> bool:
        """Check if connected to NATS.
        
        Returns:
            True if connected, False otherwise
        """
        if not self.nc:
            return False
        return self.nc.is_connected
    
    def get_stream_context(self):
        """Get JetStream context.
        
        Returns:
            JetStream context object
            
        Raises:
            RuntimeError: If not connected
        """
        if not self.js:
            raise RuntimeError("Not connected to NATS. Call connect() first.")
        return self.js
