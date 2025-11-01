"""Audit operation value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AuditOperation:
    """
    Immutable value object representing an operation to be audited.
    
    Following DDD principles:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - Encapsulates audit operation data
    """

    operation_name: str
    operation_params: dict[str, Any]

    def __post_init__(self) -> None:
        """
        Validate value object invariants (fail-fast).
        
        Raises:
            ValueError: If any invariant is violated
        """
        if not self.operation_name or not self.operation_name.strip():
            raise ValueError("operation_name is required and cannot be empty (fail-fast)")
        
        if self.operation_params is None:
            raise ValueError("operation_params is required (use empty dict if no params) (fail-fast)")
        
        if not isinstance(self.operation_params, dict):
            raise ValueError("operation_params must be a dictionary (fail-fast)")

    def get_name(self) -> str:
        """
        Get operation name.
        
        Returns:
            Operation name
        """
        return self.operation_name

    def get_params(self) -> dict[str, Any]:
        """
        Get operation parameters.
        
        Returns:
            Dictionary of operation parameters
        """
        return self.operation_params

    def has_params(self) -> bool:
        """
        Check if operation has parameters.
        
        Returns:
            True if params dict is not empty, False otherwise
        """
        return len(self.operation_params) > 0

    @classmethod
    def for_run(cls, image: str, detach: bool = False) -> AuditOperation:
        """
        Create audit operation for 'run' command.
        
        Args:
            image: Container image name
            detach: Whether container ran in detached mode
            
        Returns:
            AuditOperation for run command
        """
        return cls(
            operation_name="run",
            operation_params={"image": image, "detach": detach}
        )

    @classmethod
    def for_build(cls, context: str, dockerfile: str) -> AuditOperation:
        """
        Create audit operation for 'build' command.
        
        Args:
            context: Build context path
            dockerfile: Dockerfile path
            
        Returns:
            AuditOperation for build command
        """
        return cls(
            operation_name="build",
            operation_params={"context": context, "dockerfile": dockerfile}
        )

    @classmethod
    def for_exec(cls, container: str, command: list[str]) -> AuditOperation:
        """
        Create audit operation for 'exec' command.
        
        Args:
            container: Container name or ID
            command: Command executed in container
            
        Returns:
            AuditOperation for exec command
        """
        return cls(
            operation_name="exec",
            operation_params={"container": container, "command": command}
        )

    @classmethod
    def simple(cls, operation_name: str) -> AuditOperation:
        """
        Create audit operation with no parameters.
        
        Args:
            operation_name: Name of the operation
            
        Returns:
            AuditOperation with empty params
        """
        return cls(operation_name=operation_name, operation_params={})

