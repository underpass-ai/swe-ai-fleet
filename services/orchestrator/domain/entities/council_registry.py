"""Council registry entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CouncilRegistry:
    """Entity representing a registry of councils.
    
    Manages councils (deliberation use cases) and their associated agents.
    Applies "Tell, Don't Ask" principle by encapsulating council operations.
    
    Attributes:
        councils: Dictionary mapping role names to council instances
        council_agents: Dictionary mapping role names to agent lists
    """
    
    councils: dict[str, Any] = field(default_factory=dict)
    council_agents: dict[str, list[Any]] = field(default_factory=dict)
    
    def register_council(
        self,
        role: str,
        council: Any,
        agents: list[Any]
    ) -> None:
        """Register a new council for a role.
        
        Tell, Don't Ask: Tell registry to register council
        instead of asking if it exists and then setting it.
        
        Args:
            role: Role name for the council
            council: Council (Deliberate use case) instance
            agents: List of agents in the council
            
        Raises:
            ValueError: If council already exists for role
        """
        if self.has_council(role):
            raise ValueError(f"Council for role {role} already exists")
        
        self.councils[role] = council
        self.council_agents[role] = agents
    
    def update_council(
        self,
        role: str,
        council: Any,
        agents: list[Any]
    ) -> None:
        """Update an existing council.
        
        Tell, Don't Ask: Tell registry to update council.
        
        Args:
            role: Role name for the council
            council: Updated council instance
            agents: Updated list of agents
            
        Raises:
            ValueError: If council doesn't exist for role
        """
        if not self.has_council(role):
            raise ValueError(f"Council for role {role} not found")
        
        self.councils[role] = council
        self.council_agents[role] = agents
    
    def get_council(self, role: str) -> Any:
        """Get council for a role.
        
        Applies fail-fast principle: raises RuntimeError if council not found
        instead of returning None, preventing invalid states from propagating.
        
        Tell, Don't Ask: Tell registry to get council
        instead of asking for councils dict.
        
        Args:
            role: Role name
            
        Returns:
            Council instance
            
        Raises:
            RuntimeError: If council not found for the given role
            
        Example:
            >>> registry = CouncilRegistry()
            >>> council = registry.get_council("Coder")  # Raises if not found
        """
        if not self.has_council(role):
            raise RuntimeError(
                f"Council for role '{role}' not found in registry. "
                f"Available roles: {list(self.councils.keys())}. "
                f"Create council first with register_council()."
            )
        
        return self.councils[role]
    
    def get_agents(self, role: str) -> list[Any]:
        """Get agents for a council.
        
        Args:
            role: Role name
            
        Returns:
            List of agents
            
        Raises:
            ValueError: If council not found
        """
        if not self.has_council(role):
            raise ValueError(f"Council for role {role} not found")
        
        return self.council_agents[role]
    
    def delete_council(self, role: str) -> tuple[Any, int]:
        """Delete a council and return its info.
        
        Tell, Don't Ask: Tell registry to delete council
        and return relevant info in one operation.
        
        Args:
            role: Role name
            
        Returns:
            Tuple of (council, agents_count)
            
        Raises:
            ValueError: If council not found
        """
        if not self.has_council(role):
            raise ValueError(f"Council for role {role} not found")
        
        council = self.councils.pop(role)
        agents = self.council_agents.pop(role)
        
        return council, len(agents)
    
    def has_council(self, role: str) -> bool:
        """Check if council exists for role.
        
        Args:
            role: Role name
            
        Returns:
            True if council exists, False otherwise
        """
        return role in self.councils
    
    def get_all_roles(self) -> list[str]:
        """Get all registered role names.
        
        Returns:
            List of role names
        """
        return list(self.councils.keys())
    
    def get_all_councils(self) -> dict[str, Any]:
        """Get all councils.
        
        Returns:
            Dictionary of role -> council
        """
        return self.councils.copy()
    
    def get_councils_with_agents(self) -> list[tuple[str, Any, list[Any]]]:
        """Get all councils with their agents.
        
        Tell, Don't Ask: Tell registry to provide complete info
        instead of asking for multiple dicts and combining externally.
        
        Returns:
            List of tuples (role, council, agents)
        """
        result = []
        for role, council in self.councils.items():
            agents = self.council_agents.get(role, [])
            result.append((role, council, agents))
        return result
    
    @property
    def count(self) -> int:
        """Get number of registered councils."""
        return len(self.councils)
    
    @property
    def is_empty(self) -> bool:
        """Check if registry is empty."""
        return self.count == 0
    
    def clear(self) -> None:
        """Remove all councils from registry."""
        self.councils.clear()
        self.council_agents.clear()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert registry to dictionary."""
        return {
            "count": self.count,
            "roles": self.get_all_roles(),
        }
    
    def __len__(self) -> int:
        """Get number of councils."""
        return self.count
    
    def __contains__(self, role: str) -> bool:
        """Check if role exists in registry."""
        return self.has_council(role)
    
    def __iter__(self):
        """Iterate over (role, council) pairs."""
        return iter(self.councils.items())

