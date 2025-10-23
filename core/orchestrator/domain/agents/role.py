"""Role domain object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Role:
    """Domain object representing a role in the system.
    
    Encapsulates a role with its name and associated capabilities.
    """
    
    name: str
    capabilities: list[str] | None = None
    
    def __str__(self) -> str:
        """String representation of the role."""
        return self.name
    
    @property
    def is_devops(self) -> bool:
        """Check if this is a DevOps role."""
        return self.name.lower() in {"devops", "dev-ops", "dev_ops"}
    
    @property
    def is_developer(self) -> bool:
        """Check if this is a developer role."""
        return self.name.lower() in {"developer", "dev", "programmer", "engineer"}
    
    @property
    def is_architect(self) -> bool:
        """Check if this is an architect role."""
        return self.name.lower() in {"architect", "architecture", "solution_architect"}
    
    def has_capability(self, capability: str) -> bool:
        """Check if the role has a specific capability.
        
        Args:
            capability: The capability to check for
            
        Returns:
            True if the role has the capability, False otherwise
        """
        if self.capabilities is None:
            return False
        return capability.lower() in [c.lower() for c in self.capabilities]
    
    @classmethod
    def from_string(cls, name: str, capabilities: list[str] | None = None) -> Role:
        """Create a Role from a string name.
        
        Args:
            name: The role name
            capabilities: Optional list of capabilities
            
        Returns:
            Role object
        """
        return cls(name=name, capabilities=capabilities)
