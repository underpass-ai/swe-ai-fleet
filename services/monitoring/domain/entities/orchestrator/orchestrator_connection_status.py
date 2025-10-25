"""Orchestrator connection status value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OrchestratorConnectionStatus:
    """Value object representing orchestrator connection status.
    
    This immutable value object encapsulates the connection status
    and metrics of the orchestrator service. It follows the Value Object pattern from DDD.
    
    Attributes:
        connected: Whether the orchestrator is connected
        error: Error message if connection failed, None if connected
        total_councils: Total number of councils in the orchestrator
        total_agents: Total number of agents across all councils
    """
    
    connected: bool
    error: str | None
    total_councils: int
    total_agents: int
    
    @classmethod
    def create_connected(cls, total_councils: int, total_agents: int) -> OrchestratorConnectionStatus:
        """Create connected status.
        
        Args:
            total_councils: Total number of councils
            total_agents: Total number of agents
            
        Returns:
            OrchestratorConnectionStatus with connected=True
        """
        if total_councils < 0:
            raise ValueError("Total councils cannot be negative.")
        if total_agents < 0:
            raise ValueError("Total agents cannot be negative.")
        
        return cls(
            connected=True,
            error=None,
            total_councils=total_councils,
            total_agents=total_agents
        )
    
    @classmethod
    def create_disconnected(cls, error: str, total_councils: int = 0, total_agents: int = 0) -> OrchestratorConnectionStatus:
        """Create disconnected status.
        
        Args:
            error: Error message explaining disconnection
            total_councils: Total number of councils (default 0)
            total_agents: Total number of agents (default 0)
            
        Returns:
            OrchestratorConnectionStatus with connected=False
        """
        if not error or not error.strip():
            raise ValueError("Error message cannot be empty for disconnected status.")
        if total_councils < 0:
            raise ValueError("Total councils cannot be negative.")
        if total_agents < 0:
            raise ValueError("Total agents cannot be negative.")
        
        return cls(
            connected=False,
            error=error.strip(),
            total_councils=total_councils,
            total_agents=total_agents
        )
    
    def is_connected(self) -> bool:
        """Check if orchestrator is connected.
        
        Tell, Don't Ask: Tell status to check if connected
        instead of asking for connected field externally.
        
        Returns:
            True if connected, False otherwise
        """
        return self.connected
    
    def is_disconnected(self) -> bool:
        """Check if orchestrator is disconnected.
        
        Tell, Don't Ask: Tell status to check if disconnected.
        
        Returns:
            True if disconnected, False otherwise
        """
        return not self.connected
    
    def has_error(self) -> bool:
        """Check if there's an error.
        
        Tell, Don't Ask: Tell status to check if has error.
        
        Returns:
            True if there's an error, False otherwise
        """
        return self.error is not None and bool(self.error.strip())
    
    def get_error_message(self) -> str:
        """Get error message.
        
        Tell, Don't Ask: Tell status to provide error message.
        
        Returns:
            Error message if available, empty string otherwise
        """
        return self.error or ""
    
    def has_councils(self) -> bool:
        """Check if orchestrator has any councils.
        
        Tell, Don't Ask: Tell status to check if has councils.
        
        Returns:
            True if has councils, False otherwise
        """
        return self.total_councils > 0
    
    def has_agents(self) -> bool:
        """Check if orchestrator has any agents.
        
        Tell, Don't Ask: Tell status to check if has agents.
        
        Returns:
            True if has agents, False otherwise
        """
        return self.total_agents > 0
    
    def is_healthy(self) -> bool:
        """Check if orchestrator is healthy.
        
        Tell, Don't Ask: Tell status to check if healthy.
        Healthy means connected, no errors, and has councils/agents.
        
        Returns:
            True if healthy, False otherwise
        """
        return (
            self.connected and
            self.error is None and
            self.total_councils > 0 and
            self.total_agents > 0
        )
    
    def get_status_summary(self) -> str:
        """Get human-readable status summary.
        
        Tell, Don't Ask: Tell status to provide summary.
        
        Returns:
            Formatted status summary
        """
        if self.connected:
            return f"Connected ({self.total_councils} councils, {self.total_agents} agents)"
        else:
            error_msg = f" - {self.error}" if self.error else ""
            return f"Disconnected{error_msg}"
    
    def get_metrics_summary(self) -> dict[str, int]:
        """Get metrics summary.
        
        Tell, Don't Ask: Tell status to provide metrics summary.
        
        Returns:
            Dictionary with metrics
        """
        return {
            "total_councils": self.total_councils,
            "total_agents": self.total_agents,
            "connected": 1 if self.connected else 0,
            "has_error": 1 if self.has_error() else 0
        }
    
    def to_dict(self) -> dict:
        """Convert connection status to dictionary representation.
        
        Used for serialization and API responses.
        
        Returns:
            Dictionary with connection status information
        """
        return {
            "connected": self.connected,
            "error": self.error,
            "total_councils": self.total_councils,
            "total_agents": self.total_agents,
            "is_healthy": self.is_healthy(),
            "status_summary": self.get_status_summary(),
            "metrics_summary": self.get_metrics_summary()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> OrchestratorConnectionStatus:
        """Create OrchestratorConnectionStatus from dictionary.
        
        Factory method for creating OrchestratorConnectionStatus from serialized data.
        
        Args:
            data: Dictionary with connection status information
            
        Returns:
            OrchestratorConnectionStatus instance
            
        Raises:
            ValueError: If required fields are missing
        """
        required_fields = {"connected", "total_councils", "total_agents"}
        missing_fields = required_fields - set(data.keys())
        
        if missing_fields:
            raise ValueError(
                f"Missing required fields: {', '.join(missing_fields)}"
            )
        
        return cls(
            connected=data["connected"],
            error=data.get("error"),  # Optional field
            total_councils=data["total_councils"],
            total_agents=data["total_agents"]
        )
    
    @classmethod
    def create_connected_status(
        cls,
        total_councils: int,
        total_agents: int
    ) -> OrchestratorConnectionStatus:
        """Create connected status.
        
        Factory method for creating connected status.
        
        Args:
            total_councils: Number of councils
            total_agents: Number of agents
            
        Returns:
            OrchestratorConnectionStatus instance for connected state
        """
        return cls(
            connected=True,
            error=None,
            total_councils=total_councils,
            total_agents=total_agents
        )
    
    @classmethod
    def create_disconnected_status(
        cls,
        error: str,
        total_councils: int = 0,
        total_agents: int = 0
    ) -> OrchestratorConnectionStatus:
        """Create disconnected status.
        
        Factory method for creating disconnected status.
        
        Args:
            error: Error message
            total_councils: Number of councils (default 0)
            total_agents: Number of agents (default 0)
            
        Returns:
            OrchestratorConnectionStatus instance for disconnected state
        """
        return cls(
            connected=False,
            error=error,
            total_councils=total_councils,
            total_agents=total_agents
        )
    
    @classmethod
    def create_empty_status(cls) -> OrchestratorConnectionStatus:
        """Create empty status (disconnected with no metrics).
        
        Factory method for creating empty status.
        
        Returns:
            OrchestratorConnectionStatus instance for empty state
        """
        return cls(
            connected=False,
            error="Not initialized",
            total_councils=0,
            total_agents=0
        )
