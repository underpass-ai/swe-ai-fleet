"""Agent progress update entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentProgressUpdate:
    """Event received with agent progress updates.
    
    Origin: Ray Executor / Agent Service
    Subject: agent.response.progress
    
    Attributes:
        task_id: Task identifier
        agent_id: Agent identifier
        progress_pct: Progress percentage (0-100)
        message: Progress message
    """
    
    task_id: str
    agent_id: str
    progress_pct: int
    message: str
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentProgressUpdate:
        """Create event from dictionary.
        
        Args:
            data: Event data from NATS message
            
        Returns:
            AgentProgressUpdate instance
            
        Raises:
            ValueError: If required fields missing
        """
        required = ["task_id", "agent_id"]
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        
        return cls(
            task_id=data["task_id"],
            agent_id=data["agent_id"],
            progress_pct=data.get("progress_pct", 0),
            message=data.get("message", ""),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "progress_pct": self.progress_pct,
            "message": self.message,
        }

