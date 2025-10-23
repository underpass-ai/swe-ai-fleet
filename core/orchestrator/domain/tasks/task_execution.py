"""Domain entities for task execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .task_status import TaskStatus


@dataclass(frozen=True)
class TaskExecutionResult:
    """Domain entity representing the result of a task execution.
    
    Encapsulates the outcome, artifacts, and metadata of a completed task.
    """
    
    task_id: str
    status: TaskStatus
    artifacts_dir: str
    exit_code: int
    
    @property
    def is_successful(self) -> bool:
        """Check if the task execution was successful."""
        return self.exit_code == 0 and self.status.is_success
    
    @property
    def is_failed(self) -> bool:
        """Check if the task execution failed."""
        return self.exit_code != 0 or self.status.is_failure
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the execution result to a dictionary format."""
        return {
            "status": self.status.value,
            "task_id": self.task_id,
            "artifacts": self.artifacts_dir,
            "exit_code": self.exit_code,
        }
    
    @classmethod
    def from_runner_result(cls, task_id: str, runner_result: dict[str, Any]) -> TaskExecutionResult:
        """Create a TaskExecutionResult from a runner execution result.
        
        Args:
            task_id: The ID of the executed task
            runner_result: Raw result from the task runner
            
        Returns:
            A TaskExecutionResult with the appropriate status based on exit code
        """
        exit_code = runner_result.get("exit_code", 1)
        status = TaskStatus.DONE if exit_code == 0 else TaskStatus.FAILED
        
        return cls(
            task_id=task_id,
            status=status,
            artifacts_dir=runner_result.get("artifacts_dir", ""),
            exit_code=exit_code,
        )
