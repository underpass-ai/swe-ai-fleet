"""Agent failure message entity for deliberation tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentFailureMessage:
    """Message received when an agent fails during deliberation.
    
    Origin: Ray Executor (internal deliberation tracking)
    Subject: deliberation.agent.failed
    
    Attributes:
        task_id: Task/deliberation identifier
        agent_id: Agent identifier
        error: Error message
        timestamp: Event timestamp (ISO format)
    """
    
    task_id: str
    agent_id: str
    error: str
    timestamp: str
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentFailureMessage:
        """Create message from dictionary.
        
        Args:
            data: Message data from NATS
            
        Returns:
            AgentFailureMessage instance
            
        Raises:
            ValueError: If required fields missing
        """
        required = ["task_id"]
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        
        return cls(
            task_id=data["task_id"],
            agent_id=data.get("agent_id", "unknown"),
            error=data.get("error", "Unknown error"),
            timestamp=data.get("timestamp", ""),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "error": self.error,
            "timestamp": self.timestamp,
        }

