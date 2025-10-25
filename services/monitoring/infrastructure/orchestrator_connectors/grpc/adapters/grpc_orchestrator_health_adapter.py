"""gRPC orchestrator health adapter.

This adapter handles only orchestrator health checking,
following the Single Responsibility Principle.
"""

import logging

import grpc

from services.monitoring.domain.ports.orchestrator.orchestrator_health_port import OrchestratorHealthPort
from .grpc_connection_adapter import GrpcConnectionAdapter

logger = logging.getLogger(__name__)


class GrpcOrchestratorHealthAdapter(OrchestratorHealthPort):
    """gRPC adapter for orchestrator health checking.
    
    This adapter handles only orchestrator health checking,
    following the Single Responsibility Principle.
    """
    
    def __init__(self, connection_adapter: GrpcConnectionAdapter):
        """Initialize gRPC orchestrator health adapter.
        
        Args:
            connection_adapter: Injected gRPC connection adapter
        """
        self._connection = connection_adapter
    
    async def is_orchestrator_available(self) -> bool:
        """Check if orchestrator service is available via gRPC.
        
        Performs a lightweight check by attempting to connect to the
        orchestrator service and making a simple request.
        
        Returns:
            True if orchestrator is available, False otherwise
        """
        try:
            self._connection.ensure_connection()
            
            # Import generated gRPC stubs
            from gen import orchestrator_pb2, orchestrator_pb2_grpc
            
            # Create gRPC stub
            stub = orchestrator_pb2_grpc.OrchestratorServiceStub(self._connection.get_channel())
            
            # Make a simple request to check availability
            request = orchestrator_pb2.ListCouncilsRequest(include_agents=False)
            await stub.ListCouncils(request)
            
            logger.info("✅ Orchestrator service is available")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Orchestrator service is not available: {e}")
            self._connection.close_connection()
            return False
    
    async def get_connection_status(self) -> bool:
        """Get orchestrator connection status.
        
        Returns a simple boolean indicating whether the orchestrator
        service is currently connected and operational.
        
        Returns:
            True if connected, False otherwise
        """
        return self._connection.is_connected()
