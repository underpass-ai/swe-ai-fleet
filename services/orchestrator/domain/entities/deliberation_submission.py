"""Deliberation submission entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DeliberationSubmission:
    """Entity representing a deliberation submission result.
    
    Encapsulates the result of submitting a deliberation to Ray Executor.
    
    Attributes:
        deliberation_id: Unique deliberation identifier
        status: Submission status
        message: Status message
    """
    
    deliberation_id: str
    status: str
    message: str
    
    @property
    def is_submitted(self) -> bool:
        """Check if deliberation was submitted successfully."""
        return self.status.lower() in ("submitted", "accepted", "success")
    
    @property
    def is_failed(self) -> bool:
        """Check if submission failed."""
        return self.status.lower() in ("failed", "error", "rejected")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "deliberation_id": self.deliberation_id,
            "status": self.status,
            "message": self.message,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeliberationSubmission:
        """Create from dictionary."""
        return cls(
            deliberation_id=data["deliberation_id"],
            status=data["status"],
            message=data["message"],
        )

