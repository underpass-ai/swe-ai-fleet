"""Adapter: gRPC council queries to orchestrator service."""
import logging

import grpc

from ......domain.entities.orchestrator import (
    Agent,
    Council,
    CouncilsCollection,
)
from ......domain.ports.orchestrator import CouncilQueryPort

logger = logging.getLogger(__name__)


class GRPCCouncilQueryAdapter(CouncilQueryPort):
    """gRPC implementation of council query operations."""
    
    def __init__(self, channel: grpc.aio.Channel | None = None):
        """Initialize gRPC council query adapter.
        
        Args:
            channel: gRPC channel to orchestrator (required)
        """
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
            # Return error council instead of empty collection
            error_council = Council.create(
                role="ERROR",
                agents=[],
                status="unknown",
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
            
            # Transform gRPC response to domain entities
            councils = []
            for council_info in response.councils:
                # Build agents list
                agents = []
                if council_info.agents:
                    for agent_info in council_info.agents:
                        agent = Agent.create(
                            agent_id=agent_info.agent_id,
                            status=agent_info.status or "idle"
                        )
                        agents.append(agent)
                else:
                    # Fallback: create placeholder agents if not included
                    for i in range(council_info.num_agents):
                        agent = Agent.create(
                            agent_id=f"agent-{council_info.role.lower()}-{i+1:03d}",
                            status="idle"
                        )
                        agents.append(agent)
                
                # Create council domain entity
                council = Council.create(
                    role=council_info.role,
                    agents=agents,
                    status="active" if council_info.status == "active" else "idle",
                    model=council_info.model or "unknown"
                )
                councils.append(council)
            
            result = CouncilsCollection.create(councils)
            logger.debug(f"✅ Retrieved {result.total_councils} councils, "
                        f"{result.total_agents} total agents")
            return result
            
        except grpc.RpcError as e:
            logger.error(f"❌ gRPC error getting councils: {e.code()} - {e.details()}")
            # Return error council instead of empty collection
            error_council = Council.create(
                role="ERROR",
                agents=[],
                status="unknown",
                model=f"gRPC Error: {e.details()}"
            )
            return CouncilsCollection.create([error_council])
        except Exception as e:
            logger.error(f"❌ Failed to get councils: {e}", exc_info=True)
            # Return error council instead of empty collection
            error_council = Council.create(
                role="ERROR",
                agents=[],
                status="unknown",
                model=f"Error: {str(e)}"
            )
            return CouncilsCollection.create([error_council])
