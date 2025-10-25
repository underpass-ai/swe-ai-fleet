"""Agent information value object."""

from __future__ import annotations

from dataclasses import dataclass

from .agent_role import AgentRole
from .agent_status import AgentStatus


@dataclass(frozen=True)
class AgentInfo:
    """Value object representing agent information.
    
    This immutable value object encapsulates all information about a single agent
    in the orchestrator system. It follows the Value Object pattern from DDD.
    
    Attributes:
        agent_id: Unique agent identifier (e.g., "agent-dev-001")
        role: Agent role (e.g., "DEV", "QA", "ARCHITECT")
        status: Agent status (e.g., "ready", "idle", "busy")
    """
    
    agent_id: str
    role: str
    status: str
    
    @classmethod
    def create(cls, agent_id: str, role: str, status: str) -> AgentInfo:
        """Create AgentInfo with validation.
        
        Args:
            agent_id: Unique identifier for the agent
            role: The role of the agent
            status: The current status of the agent
            
        Returns:
            AgentInfo instance
            
        Raises:
            ValueError: If any field is empty or invalid
        """
        # Validate required fields
        if not agent_id or not agent_id.strip():
            raise ValueError("Agent ID cannot be empty")
        
        if not role or not role.strip():
            raise ValueError("Agent role cannot be empty")
        
        if not status or not status.strip():
            raise ValueError("Agent status cannot be empty")
        
        # Use centralized validation
        AgentRole.validate_role(role)
        AgentStatus.validate_status(status)
        
        return cls(
            agent_id=agent_id.strip(),
            role=role,
            status=status
        )
    
    def is_ready(self) -> bool:
        """Check if agent is ready for work.
        
        Tell, Don't Ask: Tell agent to check if it's ready
        instead of asking for status and checking externally.
        
        Returns:
            True if agent is ready, False otherwise
        """
        return AgentStatus.is_ready_status(self.status)
    
    def is_busy(self) -> bool:
        """Check if agent is currently busy.
        
        Tell, Don't Ask: Tell agent to check if it's busy.
        
        Returns:
            True if agent is busy, False otherwise
        """
        return AgentStatus.is_busy_status(self.status)
    
    def is_offline(self) -> bool:
        """Check if agent is offline.
        
        Tell, Don't Ask: Tell agent to check if it's offline.
        
        Returns:
            True if agent is offline, False otherwise
        """
        return AgentStatus.is_offline_status(self.status)
    
    def get_display_name(self) -> str:
        """Get human-readable display name for the agent.
        
        Tell, Don't Ask: Tell agent to provide its display name.
        
        Returns:
            Formatted display name (e.g., "DEV Agent (agent-dev-001)")
        """
        return f"{self.role} Agent ({self.agent_id})"
    
    def get_role_emoji(self) -> str:
        """Get emoji representation for the agent's role.
        
        Tell, Don't Ask: Tell agent to provide its role emoji.
        
        Returns:
            Emoji string for the role
        """
        return AgentRole.get_role_emoji(self.role)
    
    def validate_role_consistency(self, expected_role: str) -> None:
        """Validate that agent's role matches expected role.
        
        Tell, Don't Ask: Tell agent to validate its role consistency.
        
        Args:
            expected_role: The expected role for this agent
            
        Raises:
            ValueError: If agent's role doesn't match expected role
        """
        if self.role != expected_role:
            raise ValueError(
                f"Agent {self.agent_id} has role '{self.role}' "
                f"but expected role is '{expected_role}'"
            )
    
    def to_dict(self) -> dict[str, str]:
        """Convert agent info to dictionary representation.
        
        Used for serialization and API responses.
        
        Returns:
            Dictionary with agent information
        """
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "status": self.status,
            "display_name": self.get_display_name(),
            "emoji": self.get_role_emoji()
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, str]) -> AgentInfo:
        """Create AgentInfo from dictionary.
        
        Factory method for creating AgentInfo from serialized data.
        
        Args:
            data: Dictionary with agent information
            
        Returns:
            AgentInfo instance
            
        Raises:
            ValueError: If required fields are missing
        """
        required_fields = {"agent_id", "role", "status"}
        missing_fields = required_fields - set(data.keys())
        
        if missing_fields:
            raise ValueError(
                f"Missing required fields: {', '.join(missing_fields)}"
            )
        
        return cls(
            agent_id=data["agent_id"],
            role=data["role"],
            status=data["status"]
        )
