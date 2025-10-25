"""Orchestrator health port for monitoring."""

from __future__ import annotations

from abc import ABC, abstractmethod


class OrchestratorHealthPort(ABC):
    """Port for checking orchestrator health and availability.
    
    This port defines the contract for checking orchestrator service health
    and availability. It follows the Interface Segregation Principle by
    focusing solely on health-related operations.
    
    The port is designed to be implemented by adapters that handle the actual
    communication with the orchestrator service.
    """
    
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
