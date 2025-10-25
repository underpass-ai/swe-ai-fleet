"""gRPC connection adapter for orchestrator service.

This adapter handles only the gRPC connection management,
following the Single Responsibility Principle.
"""

import logging
import os

import grpc

logger = logging.getLogger(__name__)


class GrpcConnectionAdapter:
    """gRPC connection adapter for orchestrator service.
    
    This adapter handles only gRPC connection management,
    following the Single Responsibility Principle.
    """
    
    def __init__(self, orchestrator_address: str | None = None):
        """Initialize gRPC connection adapter.
        
        Args:
            orchestrator_address: Optional orchestrator service address.
                If not provided, uses ORCHESTRATOR_ADDRESS environment variable
                or defaults to cluster service address.
        """
        self.orchestrator_address = (
            orchestrator_address or
            os.getenv(
                "ORCHESTRATOR_ADDRESS",
                "orchestrator.swe-ai-fleet.svc.cluster.local:50055"
            )
        )
        self.channel: grpc.aio.Channel | None = None
        self._connected = False
    
    def ensure_connection(self) -> None:
        """Ensure gRPC connection is established.
        
        Raises:
            ConnectionError: If unable to establish connection
        """
        if not self._connected or self.channel is None:
            try:
                self.channel = grpc.aio.insecure_channel(self.orchestrator_address)
                self._connected = True
                logger.info(f"✅ Connected to Orchestrator at {self.orchestrator_address}")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Orchestrator: {e}")
                self._connected = False
                raise ConnectionError(f"Failed to connect to orchestrator: {e}") from e
    
    def close_connection(self) -> None:
        """Close gRPC connection."""
        if self.channel:
            self.channel.close()
            self.channel = None
            self._connected = False
            logger.info("🔌 Closed Orchestrator connection")
    
    def is_connected(self) -> bool:
        """Check if gRPC connection is active.
        
        Returns:
            True if connected, False otherwise
        """
        return self._connected and self.channel is not None
    
    def get_channel(self) -> grpc.aio.Channel:
        """Get the gRPC channel.
        
        Returns:
            Active gRPC channel
            
        Raises:
            ConnectionError: If not connected
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to orchestrator")
        return self.channel
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.ensure_connection()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.close_connection()
