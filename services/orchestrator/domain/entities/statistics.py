"""Statistics entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrchestratorStatistics:
    """Domain entity representing orchestrator statistics.
    
    Tracks metrics about deliberations and orchestrations performed
    by the orchestrator service.
    
    Attributes:
        total_deliberations: Total number of deliberations executed
        total_orchestrations: Total number of orchestrations executed
        total_duration_ms: Total cumulative duration in milliseconds
        role_counts: Count of operations per role
    """
    
    total_deliberations: int = 0
    total_orchestrations: int = 0
    total_duration_ms: int = 0
    role_counts: dict[str, int] = field(default_factory=dict)
    
    def increment_deliberation(self, role: str, duration_ms: int = 0) -> None:
        """Increment deliberation count for a role.
        
        Args:
            role: Role that performed the deliberation
            duration_ms: Duration of the deliberation in milliseconds
        """
        self.total_deliberations += 1
        self.total_duration_ms += duration_ms
        self.role_counts[role] = self.role_counts.get(role, 0) + 1
    
    def increment_orchestration(self, duration_ms: int = 0) -> None:
        """Increment orchestration count.
        
        Args:
            duration_ms: Duration of the orchestration in milliseconds
        """
        self.total_orchestrations += 1
        self.total_duration_ms += duration_ms
    
    @property
    def average_duration_ms(self) -> float:
        """Calculate average duration per operation."""
        total_ops = self.total_deliberations + self.total_orchestrations
        if total_ops == 0:
            return 0.0
        return self.total_duration_ms / total_ops
    
    def to_dict(self) -> dict[str, Any]:
        """Convert statistics to dictionary."""
        return {
            "total_deliberations": self.total_deliberations,
            "total_orchestrations": self.total_orchestrations,
            "total_duration_ms": self.total_duration_ms,
            "role_counts": self.role_counts.copy(),
            "average_duration_ms": self.average_duration_ms,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrchestratorStatistics:
        """Create statistics from dictionary."""
        return cls(
            total_deliberations=data.get("total_deliberations", 0),
            total_orchestrations=data.get("total_orchestrations", 0),
            total_duration_ms=data.get("total_duration_ms", 0),
            role_counts=data.get("role_counts", {}).copy(),
        )
    
    def reset(self) -> None:
        """Reset all statistics to zero."""
        self.total_deliberations = 0
        self.total_orchestrations = 0
        self.total_duration_ms = 0
        self.role_counts.clear()

