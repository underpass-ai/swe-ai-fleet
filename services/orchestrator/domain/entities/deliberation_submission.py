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
        task_id: Original task_id from request (REQUIRED for backlog review ceremonies)
    """
    
    deliberation_id: str
    status: str
    message: str
    task_id: str | None = None  # Original task_id from request (for backlog review)
    
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
        result = {
            "deliberation_id": self.deliberation_id,
            "status": self.status,
            "message": self.message,
        }
        if self.task_id:
            result["task_id"] = self.task_id
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeliberationSubmission:
        """Create from dictionary."""
        return cls(
            deliberation_id=data["deliberation_id"],
            status=data["status"],
            message=data["message"],
            task_id=data.get("task_id"),
        )

