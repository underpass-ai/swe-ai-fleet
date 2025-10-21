"""Deliberation status entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DeliberationStatus:
    """Entity representing the status of a deliberation.
    
    Encapsulates the current state of a deliberation execution
    on the Ray cluster.
    
    Attributes:
        deliberation_id: Unique deliberation identifier
        status: Current status (pending, in_progress, completed, failed, timeout)
        result: Deliberation result if completed
        error_message: Error message if failed
    """
    
    deliberation_id: str
    status: str
    result: Any | None = None
    error_message: str | None = None
    
    @property
    def is_pending(self) -> bool:
        """Check if deliberation is pending."""
        return self.status == "pending"
    
    @property
    def is_in_progress(self) -> bool:
        """Check if deliberation is in progress."""
        return self.status == "in_progress"
    
    @property
    def is_completed(self) -> bool:
        """Check if deliberation is completed."""
        return self.status == "completed"
    
    @property
    def is_failed(self) -> bool:
        """Check if deliberation failed."""
        return self.status == "failed"
    
    @property
    def is_timeout(self) -> bool:
        """Check if deliberation timed out."""
        return self.status == "timeout"
    
    @property
    def has_error(self) -> bool:
        """Check if deliberation has error."""
        return self.error_message is not None
    
    @property
    def has_result(self) -> bool:
        """Check if deliberation has result."""
        return self.result is not None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result_dict = {
            "deliberation_id": self.deliberation_id,
            "status": self.status,
        }
        
        if self.result is not None:
            result_dict["result"] = self.result
        
        if self.error_message is not None:
            result_dict["error_message"] = self.error_message
        
        return result_dict
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeliberationStatus:
        """Create from dictionary."""
        return cls(
            deliberation_id=data["deliberation_id"],
            status=data["status"],
            result=data.get("result"),
            error_message=data.get("error_message"),
        )

