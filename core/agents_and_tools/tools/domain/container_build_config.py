"""Container build configuration value object."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContainerBuildConfig:
    """
    Immutable value object representing container build configuration.
    
    Following DDD principles:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - Self-contained business logic
    """

    context_path: str | Path = "."
    dockerfile: str = "Dockerfile"
    tag: str | None = None
    build_args: dict[str, str] | None = None
    no_cache: bool = False
    timeout: int = 600

    def __post_init__(self) -> None:
        """
        Validate value object invariants (fail-fast).
        
        Raises:
            ValueError: If any invariant is violated
        """
        if not self.context_path:
            raise ValueError("context_path is required (fail-fast)")
        
        if not self.dockerfile or not self.dockerfile.strip():
            raise ValueError("dockerfile is required and cannot be empty (fail-fast)")
        
        if not isinstance(self.timeout, int):
            raise ValueError("timeout must be an integer (fail-fast)")
        
        if self.timeout <= 0:
            raise ValueError("timeout must be positive (fail-fast)")
        
        if self.build_args is not None and not isinstance(self.build_args, dict):
            raise ValueError("build_args must be a dictionary or None (fail-fast)")
        
        if not isinstance(self.no_cache, bool):
            raise ValueError("no_cache must be a boolean (fail-fast)")

    def has_tag(self) -> bool:
        """
        Check if a tag is specified.
        
        Returns:
            True if tag is provided, False otherwise
        """
        return self.tag is not None and self.tag.strip() != ""

    def has_build_args(self) -> bool:
        """
        Check if build arguments are specified.
        
        Returns:
            True if build_args are provided, False otherwise
        """
        return self.build_args is not None and len(self.build_args) > 0

    def get_context_str(self) -> str:
        """
        Get context path as string.
        
        Returns:
            Context path as string
        """
        return str(self.context_path)

    def is_cache_disabled(self) -> bool:
        """
        Check if build cache is disabled.
        
        Returns:
            True if no_cache is enabled
        """
        return self.no_cache

    @classmethod
    def simple(cls, context_path: str = ".") -> ContainerBuildConfig:
        """
        Create simple build config with default Dockerfile.
        
        Args:
            context_path: Build context path (default: current directory)
            
        Returns:
            ContainerBuildConfig with defaults
        """
        return cls(context_path=context_path)

    @classmethod
    def with_tag(cls, context_path: str, tag: str) -> ContainerBuildConfig:
        """
        Create build config with specific tag.
        
        Args:
            context_path: Build context path
            tag: Image tag (e.g., "myapp:v1.0")
            
        Returns:
            ContainerBuildConfig with tag
        """
        return cls(context_path=context_path, tag=tag)

    @classmethod
    def with_custom_dockerfile(cls, context_path: str, dockerfile: str) -> ContainerBuildConfig:
        """
        Create build config with custom Dockerfile name.
        
        Args:
            context_path: Build context path
            dockerfile: Dockerfile name (e.g., "Dockerfile.prod")
            
        Returns:
            ContainerBuildConfig with custom dockerfile
        """
        return cls(context_path=context_path, dockerfile=dockerfile)

