"""Orchestrator query port for monitoring."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities.orchestrator.orchestrator_info import OrchestratorInfo


class OrchestratorQueryPort(ABC):
    """Port for querying orchestrator information.
    
    This port defines the contract for retrieving orchestrator information
    from external sources (e.g., gRPC, REST API). It follows the Port pattern
    from Hexagonal Architecture, isolating domain logic from infrastructure concerns.
    
    The port is designed to be implemented by adapters that handle the actual
    communication with the orchestrator service.
    """
    
    @abstractmethod
    async def get_orchestrator_info(self) -> OrchestratorInfo:
        """Get complete orchestrator information.
        
        Retrieves all orchestrator information including connection status,
        councils, and agents. This is the main entry point for orchestrator
        data retrieval.
        
        Returns:
            OrchestratorInfo aggregate root with complete orchestrator state
            
        Raises:
            ConnectionError: If unable to connect to orchestrator service
            TimeoutError: If request times out
            ValueError: If received data is invalid or malformed
        """
        pass
    
    @abstractmethod
    async def is_orchestrator_available(self) -> bool:
        """Check if orchestrator service is available.
        
        Performs a lightweight check to determine if the orchestrator
        service is reachable and responding. This is useful for health
        checks and monitoring.
        
        Returns:
            True if orchestrator is available, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_connection_status(self) -> bool:
        """Get orchestrator connection status.
        
        Returns a simple boolean indicating whether the orchestrator
        service is currently connected and operational.
        
        Returns:
            True if connected, False otherwise
        """
        pass
