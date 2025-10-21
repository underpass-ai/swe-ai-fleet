"""Role collection entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoleConfig:
    """Configuration for a role in the system.
    
    Attributes:
        name: Name of the role (e.g., "DEV", "QA", "ARCHITECT")
        replicas: Number of agent replicas for this role
        model_profile: Model profile to use for agents in this role
    """
    
    name: str
    replicas: int = 3
    model_profile: str = "default"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert role config to dictionary."""
        return {
            "name": self.name,
            "replicas": self.replicas,
            "model_profile": self.model_profile,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoleConfig:
        """Create role config from dictionary."""
        return cls(
            name=data["name"],
            replicas=data.get("replicas", 3),
            model_profile=data.get("model_profile", "default"),
        )


@dataclass
class RoleCollection:
    """Domain entity representing a collection of roles.
    
    Manages the collection of role configurations and provides
    operations for role management and querying.
    
    Attributes:
        roles: List of role configurations
    """
    
    roles: list[RoleConfig] = field(default_factory=list)
    
    def add_role(self, role: RoleConfig) -> None:
        """Add a role to the collection.
        
        Args:
            role: Role configuration to add
            
        Raises:
            ValueError: If role with same name already exists
        """
        if self.has_role(role.name):
            raise ValueError(f"Role {role.name} already exists in collection")
        
        self.roles.append(role)
    
    def remove_role(self, role_name: str) -> None:
        """Remove a role from the collection by name.
        
        Args:
            role_name: Name of the role to remove
            
        Raises:
            ValueError: If role not found in collection
        """
        role = self.get_role_by_name(role_name)
        self.roles.remove(role)
    
    def get_role_by_name(self, role_name: str) -> RoleConfig:
        """Get a role configuration by name.
        
        Args:
            role_name: Name of the role to retrieve
            
        Returns:
            The role configuration
            
        Raises:
            ValueError: If role not found in collection
        """
        for role in self.roles:
            if role.name == role_name:
                return role
        
        raise ValueError(f"Role {role_name} not found in collection")
    
    def has_role(self, role_name: str) -> bool:
        """Check if a role exists in the collection.
        
        Args:
            role_name: Name of the role to check
            
        Returns:
            True if role exists, False otherwise
        """
        try:
            self.get_role_by_name(role_name)
            return True
        except ValueError:
            return False
    
    def get_all_role_names(self) -> list[str]:
        """Get a list of all role names.
        
        Returns:
            List of role names
        """
        return [role.name for role in self.roles]
    
    def get_total_replicas(self) -> int:
        """Calculate total number of replicas across all roles.
        
        Returns:
            Total number of replicas
        """
        return sum(role.replicas for role in self.roles)
    
    @property
    def count(self) -> int:
        """Get the number of roles in the collection."""
        return len(self.roles)
    
    @property
    def is_empty(self) -> bool:
        """Check if the collection is empty."""
        return self.count == 0
    
    def clear(self) -> None:
        """Remove all roles from the collection."""
        self.roles.clear()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert collection to dictionary.
        
        Returns:
            Dictionary representation of the collection
        """
        return {
            "count": self.count,
            "total_replicas": self.get_total_replicas(),
            "roles": [role.to_dict() for role in self.roles],
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoleCollection:
        """Create role collection from dictionary.
        
        Args:
            data: Dictionary with roles list
            
        Returns:
            RoleCollection instance
        """
        roles = [RoleConfig.from_dict(role_data) for role_data in data.get("roles", [])]
        return cls(roles=roles)
    
    @classmethod
    def create_default(cls) -> RoleCollection:
        """Create a default role collection with standard roles.
        
        Returns:
            RoleCollection with default roles (DEV, QA, ARCHITECT, DEVOPS, DATA)
        """
        default_roles = [
            RoleConfig(name="DEV", replicas=3, model_profile="default"),
            RoleConfig(name="QA", replicas=3, model_profile="default"),
            RoleConfig(name="ARCHITECT", replicas=3, model_profile="default"),
            RoleConfig(name="DEVOPS", replicas=3, model_profile="default"),
            RoleConfig(name="DATA", replicas=3, model_profile="default"),
        ]
        return cls(roles=default_roles)
    
    def __len__(self) -> int:
        """Get the number of roles in the collection."""
        return self.count
    
    def __contains__(self, role_name: str) -> bool:
        """Check if a role name exists in the collection."""
        return self.has_role(role_name)
    
    def __iter__(self):
        """Iterate over roles in the collection."""
        return iter(self.roles)

