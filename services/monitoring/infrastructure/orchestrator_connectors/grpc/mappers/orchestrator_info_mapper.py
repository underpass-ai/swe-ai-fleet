"""Mapper for converting protobuf orchestrator data to domain OrchestratorInfo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from services.monitoring.domain.entities.orchestrator.orchestrator_connection_status import (
    OrchestratorConnectionStatus,
)
from services.monitoring.domain.entities.orchestrator.orchestrator_info import OrchestratorInfo

from .council_info_mapper import CouncilInfoMapper

if TYPE_CHECKING:
    # Import protobuf types only for type checking
    pass


class OrchestratorInfoMapper:
    """Mapper for converting protobuf orchestrator data to domain OrchestratorInfo.
    
    This mapper follows the Mapper pattern from Hexagonal Architecture,
    translating between infrastructure (protobuf) and domain (entities)
    layers. It orchestrates the conversion of orchestrator data including
    councils and connection status.
    """
    
    @staticmethod
    def proto_to_domain(proto_response) -> OrchestratorInfo:
        """Convert protobuf orchestrator response to domain OrchestratorInfo.
        
        Args:
            proto_response: Protobuf ListCouncilsResponse message
            
        Returns:
            OrchestratorInfo domain entity
            
        Raises:
            ValueError: If protobuf data is invalid or missing required fields
        """
        if not proto_response:
            raise ValueError("Proto response cannot be None")
        
        # Convert councils
        councils = []
        if hasattr(proto_response, 'councils') and proto_response.councils:
            for proto_council in proto_response.councils:
                try:
                    council = CouncilInfoMapper.proto_to_domain(proto_council)
                    councils.append(council)
                except ValueError as e:
                    # Log warning but continue with other councils
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to convert council: {e}")
        
        # Create connection status
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=len(councils),
            total_agents=sum(council.total_agents for council in councils)
        )
        
        # Create orchestrator info aggregate
        return OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
    
    @staticmethod
    def domain_to_proto(orchestrator_info: OrchestratorInfo) -> dict:
        """Convert domain OrchestratorInfo to protobuf-compatible dictionary.
        
        This method is provided for completeness and future use cases
        where we might need to send orchestrator information back to
        the orchestrator service.
        
        Args:
            orchestrator_info: OrchestratorInfo domain entity
            
        Returns:
            Dictionary compatible with protobuf orchestrator response
        """
        return {
            "connection_status": orchestrator_info.connection_status.to_dict(),
            "councils": [
                CouncilInfoMapper.domain_to_proto(council)
                for council in orchestrator_info.councils
            ],
            "total_councils": orchestrator_info.total_councils,
            "total_agents": orchestrator_info.total_agents,
            "is_connected": orchestrator_info.is_connected(),
            "is_healthy": orchestrator_info.is_healthy()
        }
    
    @staticmethod
    def create_disconnected_orchestrator(error: str) -> OrchestratorInfo:
        """Create a disconnected orchestrator with error information.
        
        This method creates an OrchestratorInfo representing a failed
        connection or error state, useful for error handling scenarios.
        
        Args:
            error: Error message describing the connection failure
            
        Returns:
            OrchestratorInfo in disconnected state
        """
        return OrchestratorInfo.create_disconnected_orchestrator(
            error=error,
            councils=[]
        )
    
    @staticmethod
    def create_empty_orchestrator() -> OrchestratorInfo:
        """Create an empty orchestrator (not initialized).
        
        This method creates an OrchestratorInfo representing an
        uninitialized state, useful for initial setup scenarios.
        
        Returns:
            OrchestratorInfo in empty state
        """
        return OrchestratorInfo.create_empty_orchestrator()
    
    @staticmethod
    def create_connected_orchestrator(councils: list) -> OrchestratorInfo:
        """Create a connected orchestrator with councils.
        
        This method creates an OrchestratorInfo representing a
        successful connection with council data.
        
        Args:
            councils: List of CouncilInfo entities
            
        Returns:
            OrchestratorInfo in connected state
        """
        return OrchestratorInfo.create_connected_orchestrator(councils)
