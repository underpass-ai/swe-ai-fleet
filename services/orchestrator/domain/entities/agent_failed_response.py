"""Agent failed response entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentFailedResponse:
    """Event received when an agent fails a task.
    
    Origin: Ray Executor / Agent Service
    Subject: agent.response.failed
    
    Attributes:
        task_id: Task identifier
        agent_id: Agent identifier
        story_id: Story identifier
        role: Agent role
        error: Error message
        error_type: Error type classification
        timestamp: Event timestamp (ISO format)
    """
    
    task_id: str
    agent_id: str
    story_id: str
    role: str
    error: str
    error_type: str
    timestamp: str
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentFailedResponse:
        """Create event from dictionary.
        
        Args:
            data: Event data from NATS message
            
        Returns:
            AgentFailedResponse instance
            
        Raises:
            ValueError: If required fields missing
        """
        required = ["task_id", "agent_id", "story_id", "role", "timestamp"]
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        
        return cls(
            task_id=data["task_id"],
            agent_id=data["agent_id"],
            story_id=data["story_id"],
            role=data["role"],
            error=data.get("error", "Unknown error"),
            error_type=data.get("error_type", "UNKNOWN"),
            timestamp=data["timestamp"],
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "story_id": self.story_id,
            "role": self.role,
            "error": self.error,
            "error_type": self.error_type,
            "timestamp": self.timestamp,
        }

