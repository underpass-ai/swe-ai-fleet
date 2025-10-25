"""gRPC orchestrator info adapter.

This adapter handles only orchestrator information retrieval,
following the Single Responsibility Principle.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import grpc

from services.monitoring.domain.entities.orchestrator.orchestrator_info import OrchestratorInfo
from services.monitoring.domain.ports.orchestrator.orchestrator_info_port import OrchestratorInfoPort
from .grpc_connection_adapter import GrpcConnectionAdapter
from ..mappers.orchestrator_info_mapper import OrchestratorInfoMapper

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class GrpcOrchestratorInfoAdapter(OrchestratorInfoPort):
    """gRPC adapter for orchestrator information retrieval.
    
    This adapter handles only orchestrator information retrieval,
    following the Single Responsibility Principle.
    """
    
    def __init__(self, connection_adapter: GrpcConnectionAdapter):
        """Initialize gRPC orchestrator info adapter.
        
        Args:
            connection_adapter: Injected gRPC connection adapter
        """
        self._connection = connection_adapter
    
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
            self._connection.ensure_connection()
            
            # Import generated gRPC stubs (generated during Docker build)
            from gen import orchestrator_pb2, orchestrator_pb2_grpc
            
            # Create gRPC stub
            stub = orchestrator_pb2_grpc.OrchestratorServiceStub(self._connection.get_channel())
            
            # Call ListCouncils method with include_agents=True to get agent details
            request = orchestrator_pb2.ListCouncilsRequest(include_agents=True)
            response = await stub.ListCouncils(request)
            
            # Convert protobuf response to domain entity using mapper
            orchestrator_info = OrchestratorInfoMapper.proto_to_domain(response)
            
            logger.info(
                f"✅ Retrieved orchestrator info: {orchestrator_info.total_councils} councils, "
                f"{orchestrator_info.total_agents} agents"
            )
            
            return orchestrator_info
            
        except grpc.RpcError as e:
            logger.error(f"❌ gRPC error retrieving orchestrator info: {e}")
            self._connection.close_connection()
            
            # Create disconnected orchestrator info using mapper
            return OrchestratorInfoMapper.create_disconnected_orchestrator(
                error=f"gRPC error: {e.details()}"
            )
            
        except Exception as e:
            logger.error(f"❌ Unexpected error retrieving orchestrator info: {e}")
            self._connection.close_connection()
            
            # Create disconnected orchestrator info using mapper
            return OrchestratorInfoMapper.create_disconnected_orchestrator(
                error=f"Unexpected error: {str(e)}"
            )

