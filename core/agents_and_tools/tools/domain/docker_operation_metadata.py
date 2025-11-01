"""Docker operation metadata value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class DockerOperationMetadata:
    """
    Immutable value object representing metadata for a Docker operation.
    
    Following DDD principles:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - Encapsulates operation context and details
    """

    cmd: list[str]
    image: Optional[str] = None
    detach: Optional[bool] = None
    name: Optional[str] = None
    timeout: Optional[int] = None
    error: Optional[str] = None
    container_id: Optional[str] = None
    exit_code: Optional[int] = None
    runtime: Optional[str] = None
    additional_data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """
        Validate value object invariants (fail-fast).
        
        Raises:
            ValueError: If cmd is invalid
        """
        if not self.cmd or not isinstance(self.cmd, list):
            raise ValueError("cmd is required and must be a non-empty list (fail-fast)")
        
        if len(self.cmd) == 0:
            raise ValueError("cmd cannot be empty (fail-fast)")

    def to_dict(self) -> dict[str, Any]:
        """
        Convert metadata to dictionary for serialization.
        
        Note: This method is allowed because metadata needs to be serialized
        for audit trails and logging.
        
        Returns:
            Dictionary representation with only non-None fields
        """
        result = {"cmd": self.cmd}
        
        if self.image is not None:
            result["image"] = self.image
        if self.detach is not None:
            result["detach"] = self.detach
        if self.name is not None:
            result["name"] = self.name
        if self.timeout is not None:
            result["timeout"] = self.timeout
        if self.error is not None:
            result["error"] = self.error
        if self.container_id is not None:
            result["container_id"] = self.container_id
        if self.exit_code is not None:
            result["exit_code"] = self.exit_code
        if self.runtime is not None:
            result["runtime"] = self.runtime
        if self.additional_data:
            result.update(self.additional_data)
        
        return result

    def has_error(self) -> bool:
        """
        Check if metadata contains an error.
        
        Returns:
            True if error field is present, False otherwise
        """
        return self.error is not None and self.error.strip() != ""

    def get_command_string(self) -> str:
        """
        Get command as a single string for logging.
        
        Returns:
            Space-separated command string
        """
        return " ".join(self.cmd)

    @classmethod
    def for_run(
        cls,
        cmd: list[str],
        image: str,
        detach: bool = False,
        name: Optional[str] = None,
    ) -> DockerOperationMetadata:
        """
        Create metadata for 'run' operation.
        
        Args:
            cmd: Command that was executed
            image: Container image used
            detach: Whether container ran in detached mode
            name: Container name (if any)
            
        Returns:
            DockerOperationMetadata for run operation
        """
        return cls(cmd=cmd, image=image, detach=detach, name=name)

    @classmethod
    def for_error(
        cls,
        cmd: list[str],
        error: str,
        timeout: Optional[int] = None,
    ) -> DockerOperationMetadata:
        """
        Create metadata for error scenario.
        
        Args:
            cmd: Command that failed
            error: Error message
            timeout: Timeout value if timeout error
            
        Returns:
            DockerOperationMetadata for error case
        """
        return cls(cmd=cmd, error=error, timeout=timeout)

    @classmethod
    def for_build(
        cls,
        cmd: list[str],
        context: str,
        dockerfile: str,
    ) -> DockerOperationMetadata:
        """
        Create metadata for 'build' operation.
        
        Args:
            cmd: Command that was executed
            context: Build context path
            dockerfile: Dockerfile path
            
        Returns:
            DockerOperationMetadata for build operation
        """
        return cls(
            cmd=cmd,
            additional_data={"context": context, "dockerfile": dockerfile}
        )

