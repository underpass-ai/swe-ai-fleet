"""Container run configuration value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContainerRunConfig:
    """
    Immutable value object representing container run configuration.
    
    Following DDD principles:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - Self-contained business logic
    """

    image: str
    command: list[str] | None = None
    env: dict[str, str] | None = None
    volumes: dict[str, str] | None = None
    ports: dict[str, str] | None = None
    detach: bool = False
    rm: bool = True
    name: str | None = None
    timeout: int = 300

    def __post_init__(self) -> None:
        """
        Validate value object invariants (fail-fast).
        
        Raises:
            ValueError: If any invariant is violated
        """
        if not self.image or not self.image.strip():
            raise ValueError("image is required and cannot be empty (fail-fast)")
        
        if not isinstance(self.detach, bool):
            raise ValueError("detach must be a boolean (fail-fast)")
        
        if not isinstance(self.rm, bool):
            raise ValueError("rm must be a boolean (fail-fast)")
        
        if not isinstance(self.timeout, int):
            raise ValueError("timeout must be an integer (fail-fast)")
        
        if self.timeout <= 0:
            raise ValueError("timeout must be positive (fail-fast)")
        
        # Validate optional collections are not empty dicts if provided
        if self.env is not None and not isinstance(self.env, dict):
            raise ValueError("env must be a dictionary or None (fail-fast)")
        
        if self.volumes is not None and not isinstance(self.volumes, dict):
            raise ValueError("volumes must be a dictionary or None (fail-fast)")
        
        if self.ports is not None and not isinstance(self.ports, dict):
            raise ValueError("ports must be a dictionary or None (fail-fast)")
        
        if self.command is not None and not isinstance(self.command, list):
            raise ValueError("command must be a list or None (fail-fast)")

    def has_command(self) -> bool:
        """
        Check if a custom command is specified.
        
        Returns:
            True if command is provided, False otherwise
        """
        return self.command is not None and len(self.command) > 0

    def has_env_vars(self) -> bool:
        """
        Check if environment variables are specified.
        
        Returns:
            True if env vars are provided, False otherwise
        """
        return self.env is not None and len(self.env) > 0

    def has_volumes(self) -> bool:
        """
        Check if volume mounts are specified.
        
        Returns:
            True if volumes are provided, False otherwise
        """
        return self.volumes is not None and len(self.volumes) > 0

    def has_ports(self) -> bool:
        """
        Check if port mappings are specified.
        
        Returns:
            True if ports are provided, False otherwise
        """
        return self.ports is not None and len(self.ports) > 0

    def is_detached(self) -> bool:
        """
        Check if container should run in detached mode.
        
        Returns:
            True if detached mode is enabled
        """
        return self.detach

    def should_auto_remove(self) -> bool:
        """
        Check if container should be removed after exit.
        
        Returns:
            True if auto-remove is enabled
        """
        return self.rm

    @classmethod
    def simple(cls, image: str) -> ContainerRunConfig:
        """
        Create simple run config with just image (defaults for everything else).
        
        Args:
            image: Container image to run
            
        Returns:
            ContainerRunConfig with default settings
        """
        return cls(image=image)

    @classmethod
    def interactive(cls, image: str, command: list[str]) -> ContainerRunConfig:
        """
        Create interactive run config (not detached, auto-remove).
        
        Args:
            image: Container image to run
            command: Command to execute
            
        Returns:
            ContainerRunConfig for interactive execution
        """
        return cls(image=image, command=command, detach=False, rm=True)

    @classmethod
    def daemon(cls, image: str, name: str) -> ContainerRunConfig:
        """
        Create daemon run config (detached, no auto-remove, named).
        
        Args:
            image: Container image to run
            name: Container name
            
        Returns:
            ContainerRunConfig for daemon execution
        """
        return cls(image=image, name=name, detach=True, rm=False)

