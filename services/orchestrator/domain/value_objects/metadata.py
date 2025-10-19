"""Value objects for metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OrchestratorMetadataVO:
    """Value object representing orchestrator metadata.
    
    Immutable metadata attached to orchestrator responses.
    
    Attributes:
        orchestrator_version: Version of the orchestrator service
        timestamp_ms: Timestamp when the operation occurred (milliseconds)
        execution_id: Unique identifier for the execution
    """
    
    orchestrator_version: str
    timestamp_ms: int
    execution_id: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "orchestrator_version": self.orchestrator_version,
            "timestamp_ms": self.timestamp_ms,
            "execution_id": self.execution_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrchestratorMetadataVO:
        """Create from dictionary."""
        return cls(
            orchestrator_version=data["orchestrator_version"],
            timestamp_ms=data["timestamp_ms"],
            execution_id=data["execution_id"],
        )

