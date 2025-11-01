"""Container runtime value object."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

RuntimeType = Literal["docker", "podman", "auto"]


@dataclass(frozen=True)
class ContainerRuntime:
    """
    Immutable value object representing container runtime configuration.
    
    Following DDD principles:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - Self-contained business logic
    """

    runtime_type: RuntimeType

    def __post_init__(self) -> None:
        """
        Validate value object invariants (fail-fast).
        
        Raises:
            ValueError: If runtime_type is invalid
        """
        valid_types = {"docker", "podman", "auto"}
        if self.runtime_type not in valid_types:
            raise ValueError(
                f"runtime_type must be one of {valid_types}, got: {self.runtime_type} (fail-fast)"
            )

    def is_auto(self) -> bool:
        """
        Check if runtime should be auto-detected.
        
        Returns:
            True if runtime is 'auto', False otherwise
        """
        return self.runtime_type == "auto"

    def is_docker(self) -> bool:
        """
        Check if runtime is explicitly Docker.
        
        Returns:
            True if runtime is 'docker', False otherwise
        """
        return self.runtime_type == "docker"

    def is_podman(self) -> bool:
        """
        Check if runtime is explicitly Podman.
        
        Returns:
            True if runtime is 'podman', False otherwise
        """
        return self.runtime_type == "podman"

    @classmethod
    def auto(cls) -> ContainerRuntime:
        """
        Create auto-detect runtime.
        
        Returns:
            ContainerRuntime with 'auto' type
        """
        return cls(runtime_type="auto")

    @classmethod
    def docker(cls) -> ContainerRuntime:
        """
        Create Docker runtime.
        
        Returns:
            ContainerRuntime with 'docker' type
        """
        return cls(runtime_type="docker")

    @classmethod
    def podman(cls) -> ContainerRuntime:
        """
        Create Podman runtime.
        
        Returns:
            ContainerRuntime with 'podman' type
        """
        return cls(runtime_type="podman")

    def resolve(self, detector: Callable[[], str] | None = None) -> str:
        """
        Resolve runtime to actual runtime name.
        
        Following "Tell, Don't Ask" principle: The runtime knows how to resolve itself,
        instead of clients asking about its state and deciding what to do.
        
        Args:
            detector: Optional function to detect runtime when type is 'auto'
                     (dependency injection for testability)
        
        Returns:
            Runtime name: "docker" or "podman"
            
        Raises:
            ValueError: If auto-detection is needed but no detector provided
            RuntimeError: If detector fails to find a runtime
        """
        if self.runtime_type == "docker":
            return "docker"
        elif self.runtime_type == "podman":
            return "podman"
        elif self.runtime_type == "auto":
            if not detector:
                raise ValueError(
                    "Detector function required for auto runtime resolution (fail-fast)"
                )
            return detector()
        else:
            # This should never happen due to __post_init__ validation
            raise ValueError(f"Invalid runtime type: {self.runtime_type} (fail-fast)")

