"""Container remove configuration value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContainerRemoveConfig:
    """
    Immutable value object representing container remove configuration.
    
    Following DDD principles:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - Self-contained business logic
    """

    container: str
    force: bool = False
    remove_volumes: bool = False

    def __post_init__(self) -> None:
        """
        Validate value object invariants (fail-fast).
        
        Raises:
            ValueError: If any invariant is violated
        """
        if not self.container or not self.container.strip():
            raise ValueError("container is required and cannot be empty (fail-fast)")
        
        if not isinstance(self.force, bool):
            raise ValueError("force must be a boolean (fail-fast)")
        
        if not isinstance(self.remove_volumes, bool):
            raise ValueError("remove_volumes must be a boolean (fail-fast)")

    def is_forced(self) -> bool:
        """
        Check if forced removal is enabled.
        
        Returns:
            True if force is enabled
        """
        return self.force

    def should_remove_volumes(self) -> bool:
        """
        Check if volumes should be removed.
        
        Returns:
            True if remove_volumes is enabled
        """
        return self.remove_volumes

    @classmethod
    def simple(cls, container: str) -> ContainerRemoveConfig:
        """
        Create simple remove config (no force, keep volumes).
        
        Args:
            container: Container name or ID
            
        Returns:
            ContainerRemoveConfig with safe defaults
        """
        return cls(container=container)

    @classmethod
    def force_remove(cls, container: str) -> ContainerRemoveConfig:
        """
        Create forced remove config.
        
        Args:
            container: Container name or ID
            
        Returns:
            ContainerRemoveConfig with force enabled
        """
        return cls(container=container, force=True)

    @classmethod
    def complete_remove(cls, container: str) -> ContainerRemoveConfig:
        """
        Create complete remove config (force + remove volumes).
        
        Args:
            container: Container name or ID
            
        Returns:
            ContainerRemoveConfig with force and remove_volumes enabled
        """
        return cls(container=container, force=True, remove_volumes=True)

