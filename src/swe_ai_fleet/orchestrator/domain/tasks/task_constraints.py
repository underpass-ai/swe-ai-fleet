"""Domain object for task constraints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TaskConstraints:
    """Domain object representing constraints for task execution.
    
    Encapsulates all the constraints, rubrics, and criteria that guide
    task execution and evaluation.
    """
    
    rubric: dict[str, Any]
    architect_rubric: dict[str, Any]
    cluster_spec: dict[str, Any] | None = None
    additional_constraints: dict[str, Any] | None = None
    
    def get_rubric(self) -> dict[str, Any]:
        """Get the evaluation rubric."""
        return self.rubric
    
    def get_architect_rubric(self) -> dict[str, Any]:
        """Get the architect selection rubric."""
        return self.architect_rubric
    
    def get_cluster_spec(self) -> dict[str, Any] | None:
        """Get the cluster specification if available."""
        return self.cluster_spec
    
    def get_k_value(self) -> int:
        """Get the k value for top-k selection from architect rubric."""
        return self.architect_rubric.get("k", 3)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert constraints to dictionary format."""
        result = {
            "rubric": self.rubric,
            "architect_rubric": self.architect_rubric,
        }
        
        if self.cluster_spec is not None:
            result["cluster_spec"] = self.cluster_spec
            
        if self.additional_constraints is not None:
            result.update(self.additional_constraints)
            
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskConstraints:
        """Create TaskConstraints from dictionary data."""
        return cls(
            rubric=data.get("rubric", {}),
            architect_rubric=data.get("architect_rubric", {}),
            cluster_spec=data.get("cluster_spec"),
            additional_constraints={
                k: v for k, v in data.items() 
                if k not in {"rubric", "architect_rubric", "cluster_spec"}
            } or None
        )
