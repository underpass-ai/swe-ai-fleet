"""Deliberation result data entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProposalData:
    """Data representing a proposal from an agent.
    
    Attributes:
        author_id: Agent ID that created the proposal
        author_role: Role of the agent
        content: Proposal content/code
    """
    
    author_id: str
    author_role: str
    content: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "author_id": self.author_id,
            "author_role": self.author_role,
            "content": self.content,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProposalData:
        """Create from dictionary."""
        return cls(
            author_id=data.get("author_id", ""),
            author_role=data.get("author_role", ""),
            content=data.get("content", ""),
        )


@dataclass
class AgentResultData:
    """Data representing a single agent's result.
    
    Attributes:
        agent_id: Agent identifier
        proposal: Agent's proposal
    """
    
    agent_id: str
    proposal: ProposalData
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "proposal": self.proposal.to_dict(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentResultData:
        """Create from dictionary."""
        proposal_data = data.get("proposal", {})
        return cls(
            agent_id=data.get("agent_id", ""),
            proposal=ProposalData.from_dict(proposal_data),
        )


@dataclass
class DeliberationResultData:
    """Domain entity representing complete deliberation result data.
    
    Encapsulates all data from a completed deliberation, including
    status, results, metadata, and statistics.
    
    Attributes:
        task_id: Unique task identifier
        status: Deliberation status
        duration_ms: Duration in milliseconds
        error_message: Error message if failed
        results: List of agent results
        total_agents: Total number of agents
        received_count: Number of successful responses
        failed_count: Number of failed agents
    """
    
    task_id: str
    status: str
    duration_ms: int = 0
    error_message: str = ""
    results: list[AgentResultData] = field(default_factory=list)
    total_agents: int = 0
    received_count: int = 0
    failed_count: int = 0
    
    @property
    def is_completed(self) -> bool:
        """Check if deliberation is completed."""
        return self.status == "DELIBERATION_STATUS_COMPLETED"
    
    @property
    def is_failed(self) -> bool:
        """Check if deliberation failed."""
        return self.status in ["DELIBERATION_STATUS_FAILED", "DELIBERATION_STATUS_TIMEOUT"]
    
    @property
    def has_results(self) -> bool:
        """Check if there are any results."""
        return len(self.results) > 0
    
    @property
    def winner_agent_id(self) -> str | None:
        """Get winner agent ID (first result)."""
        return self.results[0].agent_id if self.has_results else None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "results": [r.to_dict() for r in self.results],
            "total_agents": self.total_agents,
            "received_count": self.received_count,
            "failed_count": self.failed_count,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeliberationResultData:
        """Create from dictionary.
        
        Args:
            data: Dictionary containing deliberation result data
            
        Returns:
            DeliberationResultData instance
        """
        results_data = data.get("results", [])
        results = [AgentResultData.from_dict(r) for r in results_data]
        
        return cls(
            task_id=data.get("task_id", ""),
            status=data.get("status", "DELIBERATION_STATUS_UNKNOWN"),
            duration_ms=data.get("duration_ms", 0),
            error_message=data.get("error_message", ""),
            results=results,
            total_agents=data.get("total_agents", 0),
            received_count=data.get("received_count", 0),
            failed_count=data.get("failed_count", 0),
        )

