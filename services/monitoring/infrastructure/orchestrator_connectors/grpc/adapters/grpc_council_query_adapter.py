"""Adapter: gRPC council queries to orchestrator service."""
import logging

import grpc

from ......domain.entities.orchestrator import (
    CouncilsCollection,
)
from ......domain.ports.orchestrator import CouncilQueryPort

logger = logging.getLogger(__name__)


class GRPCCouncilQueryAdapter(CouncilQueryPort):
    """gRPC implementation of council query operations."""
    
    def __init__(self, mapper, channel: grpc.aio.Channel | None = None):
        """Initialize gRPC council query adapter.
        
        Args:
            mapper: CouncilInfoMapper instance (injected)
            channel: gRPC channel to orchestrator (required)
        """
        self.mapper = mapper
        self.channel = channel
    
    async def get_councils(self) -> CouncilsCollection:
        """Get all councils from orchestrator via gRPC.
        
        Returns:
            CouncilsCollection with all councils and agents
            
        Raises:
            RuntimeError: If query fails or channel not available
        """
        if not self.channel:
            logger.error("❌ gRPC channel not available for council query")
            # Create error council using injected mapper
            error_council = self.mapper.create_empty_council(
                role="ERROR",
                model="gRPC channel not available"
            )
            return CouncilsCollection.create([error_council])
        
        try:
            # Import generated gRPC stubs
            from gen import orchestrator_pb2, orchestrator_pb2_grpc
            
            # Create stub
            stub = orchestrator_pb2_grpc.OrchestratorServiceStub(self.channel)
            
            # Call ListCouncils with include_agents=True
            request = orchestrator_pb2.ListCouncilsRequest(include_agents=True)
            response = await stub.ListCouncils(request)
            
            # Transform gRPC response to domain entities using injected mapper
            councils = []
            for council_info in response.councils:
                try:
                    council = self.mapper.proto_to_domain(council_info)
                    councils.append(council)
                except ValueError as e:
                    # Log warning but continue with other councils
                    logger.warning(f"Failed to convert council: {e}")
            
            result = CouncilsCollection.create(councils)
            logger.debug(f"✅ Retrieved {result.total_councils} councils, "
                        f"{result.total_agents} total agents")
            return result
            
        except grpc.RpcError as e:
            logger.error(f"❌ gRPC error getting councils: {e.code()} - {e.details()}")
            # Create error council using injected mapper
            error_council = self.mapper.create_empty_council(
                role="ERROR",
                model=f"gRPC Error: {e.details()}"
            )
            return CouncilsCollection.create([error_council])
        except Exception as e:
            logger.error(f"❌ Failed to get councils: {e}", exc_info=True)
            # Create error council using injected mapper
            error_council = self.mapper.create_empty_council(
                role="ERROR",
                model=f"Error: {str(e)}"
            )
            return CouncilsCollection.create([error_council])
