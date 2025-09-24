"""DTO for execution responses in the orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExecutionResponseDTO:
    """Data Transfer Object for execution responses.
    
    Represents the response from an agent job execution, including
    both successful task execution and error/no-op scenarios.
    """
    
    status: str
    reason: str | None = None
    task_id: str | None = None
    artifacts: str | None = None
    
    @classmethod
    def noop(cls, reason: str) -> ExecutionResponseDTO:
        """Create a NOOP response when no task can be executed.
        
        Args:
            reason: Explanation for why no task was executed
            
        Returns:
            A NOOP execution response
        """
        return cls(
            status="NOOP",
            reason=reason,
            task_id=None,
            artifacts=None,
        )
    
    @classmethod
    def success(cls, task_id: str, artifacts: str) -> ExecutionResponseDTO:
        """Create a successful execution response.
        
        Args:
            task_id: ID of the executed task
            artifacts: Path to generated artifacts
            
        Returns:
            A successful execution response
        """
        return cls(
            status="SUCCESS",
            reason=None,
            task_id=task_id,
            artifacts=artifacts,
        )
    
    @classmethod
    def failed(cls, task_id: str, reason: str) -> ExecutionResponseDTO:
        """Create a failed execution response.
        
        Args:
            task_id: ID of the failed task
            reason: Explanation for the failure
            
        Returns:
            A failed execution response
        """
        return cls(
            status="FAILED",
            reason=reason,
            task_id=task_id,
            artifacts=None,
        )
    
    @property
    def is_noop(self) -> bool:
        """Check if this is a NOOP response."""
        return self.status == "NOOP"
    
    @property
    def is_success(self) -> bool:
        """Check if this is a successful response."""
        return self.status == "SUCCESS"
    
    @property
    def is_failed(self) -> bool:
        """Check if this is a failed response."""
        return self.status == "FAILED"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the response to a dictionary format."""
        result = {"status": self.status}
        if self.reason:
            result["reason"] = self.reason
        if self.task_id:
            result["task_id"] = self.task_id
        if self.artifacts:
            result["artifacts"] = self.artifacts
        return result
