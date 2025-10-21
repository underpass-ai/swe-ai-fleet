"""Value object for task constraints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TaskConstraintsVO:
    """Value object representing constraints for task execution.
    
    Immutable representation of all constraints, rubrics, and criteria
    that guide task execution and evaluation.
    
    Attributes:
        rubric: Main evaluation rubric (description and requirements)
        architect_rubric: Rubric for architect selection (k value and criteria)
        max_iterations: Maximum number of iterations allowed
        timeout_seconds: Timeout for execution in seconds
        metadata: Additional metadata (optional)
    """
    
    rubric: dict[str, Any]
    architect_rubric: dict[str, Any]
    max_iterations: int = 10
    timeout_seconds: int = 300
    metadata: dict[str, Any] | None = None
    
    @property
    def k_value(self) -> int:
        """Get the k value for top-k selection from architect rubric."""
        return self.architect_rubric.get("k", 3)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "rubric": self.rubric,
            "architect_rubric": self.architect_rubric,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskConstraintsVO:
        """Create from dictionary."""
        return cls(
            rubric=data.get("rubric", {}),
            architect_rubric=data.get("architect_rubric", {"k": 3}),
            max_iterations=data.get("max_iterations", 10),
            timeout_seconds=data.get("timeout_seconds", 300),
            metadata=data.get("metadata"),
        )

