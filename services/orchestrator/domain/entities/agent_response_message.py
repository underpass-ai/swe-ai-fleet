"""Agent response message entity for deliberation tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentResponseMessage:
    """Message received when an agent submits a deliberation response.
    
    Origin: Ray Executor (internal deliberation tracking)
    Subject: deliberation.agent.response
    
    Attributes:
        task_id: Task/deliberation identifier
        agent_id: Agent identifier
        role: Agent role
        proposal: Agent proposal/response
        duration_ms: Execution duration in milliseconds
        timestamp: Event timestamp (ISO format)
        num_agents: Expected number of agents (optional)
    """
    
    task_id: str
    agent_id: str
    role: str
    proposal: dict[str, Any]
    duration_ms: int
    timestamp: str
    num_agents: int | None = None
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentResponseMessage:
        """Create message from dictionary.
        
        Args:
            data: Message data from NATS
            
        Returns:
            AgentResponseMessage instance
            
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
            role=data.get("role", "unknown"),
            proposal=data.get("proposal", {}),
            duration_ms=data.get("duration_ms", 0),
            timestamp=data.get("timestamp", ""),
            num_agents=data.get("num_agents"),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary.
        
        Returns:
            Dictionary representation
        """
        result = {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "role": self.role,
            "proposal": self.proposal,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }
        if self.num_agents is not None:
            result["num_agents"] = self.num_agents
        return result

