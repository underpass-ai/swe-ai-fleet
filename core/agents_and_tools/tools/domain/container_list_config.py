"""Container list configuration value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContainerListConfig:
    """
    Immutable value object representing container list configuration.
    
    Following DDD principles:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - Self-contained business logic
    """

    all_containers: bool = False

    def __post_init__(self) -> None:
        """
        Validate value object invariants (fail-fast).
        
        Raises:
            ValueError: If any invariant is violated
        """
        if not isinstance(self.all_containers, bool):
            raise ValueError("all_containers must be a boolean (fail-fast)")

    def should_list_all(self) -> bool:
        """
        Check if all containers should be listed (including stopped).
        
        Returns:
            True if all containers should be listed
        """
        return self.all_containers

    @classmethod
    def running_only(cls) -> ContainerListConfig:
        """
        Create config to list only running containers.
        
        Returns:
            ContainerListConfig for running containers only
        """
        return cls(all_containers=False)

    @classmethod
    def all(cls) -> ContainerListConfig:
        """
        Create config to list all containers (including stopped).
        
        Returns:
            ContainerListConfig for all containers
        """
        return cls(all_containers=True)

