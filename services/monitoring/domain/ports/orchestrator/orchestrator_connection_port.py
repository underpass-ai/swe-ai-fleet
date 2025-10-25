"""Orchestrator connection port for monitoring."""

from __future__ import annotations

from abc import ABC, abstractmethod


class OrchestratorConnectionPort(ABC):
    """Port for managing orchestrator connection lifecycle.
    
    This port defines the contract for managing orchestrator service
    connections including establishment and cleanup. It follows the
    Interface Segregation Principle by focusing solely on connection
    management operations.
    
    The port is designed to be implemented by adapters that handle the actual
    gRPC connection lifecycle.
    """
    
    @abstractmethod
    async def __aenter__(self):
        """Async context manager entry.
        
        Establishes connection to the orchestrator service.
        
        Returns:
            Self for use as context manager
        """
        pass
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit.
        
        Closes connection to the orchestrator service.
        
        Args:
            exc_type: Exception type (if raised)
            exc_val: Exception value (if raised)
            exc_tb: Exception traceback (if raised)
            
        Returns:
            None or bool indicating whether exception should be suppressed
        """
        pass
