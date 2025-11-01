"""Container stop configuration value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContainerStopConfig:
    """
    Immutable value object representing container stop configuration.
    
    Following DDD principles:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - Self-contained business logic
    """

    container: str
    timeout: int = 10

    def __post_init__(self) -> None:
        """
        Validate value object invariants (fail-fast).
        
        Raises:
            ValueError: If any invariant is violated
        """
        if not self.container or not self.container.strip():
            raise ValueError("container is required and cannot be empty (fail-fast)")
        
        if not isinstance(self.timeout, int):
            raise ValueError("timeout must be an integer (fail-fast)")
        
        if self.timeout <= 0:
            raise ValueError("timeout must be positive (fail-fast)")

    @classmethod
    def quick(cls, container: str) -> ContainerStopConfig:
        """
        Create quick stop config (default timeout).
        
        Args:
            container: Container name or ID
            
        Returns:
            ContainerStopConfig with default timeout (10s)
        """
        return cls(container=container)

    @classmethod
    def graceful(cls, container: str, timeout: int = 30) -> ContainerStopConfig:
        """
        Create graceful stop config (longer timeout for cleanup).
        
        Args:
            container: Container name or ID
            timeout: Timeout in seconds for graceful shutdown
            
        Returns:
            ContainerStopConfig with custom timeout
        """
        return cls(container=container, timeout=timeout)

