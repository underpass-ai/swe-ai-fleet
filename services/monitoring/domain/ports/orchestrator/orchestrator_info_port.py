"""Orchestrator info port for monitoring."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities.orchestrator.orchestrator_info import OrchestratorInfo


class OrchestratorInfoPort(ABC):
    """Port for retrieving orchestrator information.
    
    This port defines the contract for retrieving complete orchestrator
    information including councils and agents. It follows the Interface
    Segregation Principle by focusing solely on information retrieval.
    
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
