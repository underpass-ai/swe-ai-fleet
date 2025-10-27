"""gRPC orchestrator query adapter."""

from __future__ import annotations

import logging

import grpc
from services.monitoring.domain.entities.orchestrator.orchestrator_info import OrchestratorInfo
from services.monitoring.domain.ports.orchestrator.orchestrator_query_port import OrchestratorQueryPort

logger = logging.getLogger(__name__)


class GrpcOrchestratorQueryAdapter(OrchestratorQueryPort):
    """gRPC adapter for orchestrator query operations.
    
    This adapter implements the OrchestratorQueryPort using gRPC communication
    with the orchestrator service. It handles connection management, request
    formatting, response parsing, and error handling.
    
    The adapter follows the Adapter pattern from Hexagonal Architecture,
    translating between domain entities and gRPC protocol buffers.
    """
    
    def __init__(self, orchestrator_address: str, mapper):
        """Initialize gRPC orchestrator query adapter.
        
        Args:
            orchestrator_address: Orchestrator service address (injected)
            mapper: OrchestratorInfoMapper instance (injected)
            
        Raises:
            ConnectionError: If unable to establish initial connection
            
        Note:
            Uses insecure_channel for internal cluster communication.
            TLS is handled at the Ingress level for external services.
            See: docs/microservices/ORCHESTRATOR_INTERACTIONS.md#security-considerations
        """
        self.orchestrator_address = orchestrator_address
        self.mapper = mapper
        # Internal cluster communication - TLS handled at Ingress level
        self.channel = grpc.aio.insecure_channel(self.orchestrator_address)
        self._connected = True
        logger.info(f"✅ Connected to Orchestrator at {self.orchestrator_address}")
    
    def _ensure_connection(self) -> None:
        """Ensure gRPC connection is established.
        
        Raises:
            ConnectionError: If connection is not available
        """
        if not self._connected:
            raise ConnectionError("gRPC channel not connected")
    
    def _close_connection(self) -> None:
        """Close gRPC connection."""
        if self.channel:
            self.channel.close()
        self._connected = False
        logger.info("🔌 Closed Orchestrator connection")
    
    async def get_orchestrator_info(self) -> OrchestratorInfo:
        """Get complete orchestrator information via gRPC.
        
        Retrieves all orchestrator information including connection status,
        councils, and agents by calling the orchestrator service via gRPC.
        
        Returns:
            OrchestratorInfo aggregate root with complete orchestrator state
            
        Raises:
            ConnectionError: If unable to connect to orchestrator service
            TimeoutError: If request times out
            ValueError: If received data is invalid or malformed
        """
        try:
            self._ensure_connection()
            
            # Import generated gRPC stubs (generated during Docker build)
            from gen import orchestrator_pb2, orchestrator_pb2_grpc
            
            # Create gRPC stub
            stub = orchestrator_pb2_grpc.OrchestratorServiceStub(self.channel)
            
            # Call ListCouncils method with include_agents=True to get agent details
            request = orchestrator_pb2.ListCouncilsRequest(include_agents=True)
            response = await stub.ListCouncils(request)
            
            # Convert protobuf response to domain entity using injected mapper
            orchestrator_info = self.mapper.proto_to_domain(response)
            
            logger.info(
                f"✅ Retrieved orchestrator info: {orchestrator_info.total_councils} councils, "
                f"{orchestrator_info.total_agents} agents"
            )
            
            return orchestrator_info
            
        except grpc.RpcError as e:
            logger.error(f"❌ gRPC error retrieving orchestrator info: {e}")
            self._close_connection()
            
            # Create disconnected orchestrator info using injected mapper
            return self.mapper.create_disconnected_orchestrator(
                error=f"gRPC error: {e.details()}"
            )
            
        except Exception as e:
            logger.error(f"❌ Unexpected error retrieving orchestrator info: {e}")
            self._close_connection()
            
            # Create disconnected orchestrator info using injected mapper
            return self.mapper.create_disconnected_orchestrator(
                error=f"Unexpected error: {str(e)}"
            )
    
    async def is_orchestrator_available(self) -> bool:
        """Check if orchestrator service is available via gRPC.
        
        Performs a lightweight check by attempting to connect to the
        orchestrator service and making a simple request.
        
        Returns:
            True if orchestrator is available, False otherwise
        """
        try:
            self._ensure_connection()
            
            # Import generated gRPC stubs
            from gen import orchestrator_pb2, orchestrator_pb2_grpc
            
            # Create gRPC stub
            stub = orchestrator_pb2_grpc.OrchestratorServiceStub(self.channel)
            
            # Make a simple request to check availability
            request = orchestrator_pb2.ListCouncilsRequest(include_agents=False)
            response = await stub.ListCouncils(request)
            
            # Use injected mapper to validate response structure
            orchestrator_info = self.mapper.proto_to_domain(response)
            
            logger.info(f"✅ Orchestrator service is available: {orchestrator_info.total_councils} councils")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Orchestrator service is not available: {e}")
            self._close_connection()
            return False
    
    async def get_connection_status(self) -> bool:
        """Get orchestrator connection status.
        
        Returns a simple boolean indicating whether the orchestrator
        service is currently connected and operational.
        
        Returns:
            True if connected, False otherwise
        """
        return self._connected and self.channel is not None
    
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._ensure_connection()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self._close_connection()
