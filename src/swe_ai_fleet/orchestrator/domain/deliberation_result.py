"""Domain object for deliberation results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .agents.agent import Agent
from .check_results import CheckSuiteResult


@dataclass(frozen=True)
class Proposal:
    """Domain object representing a proposal from an agent."""
    
    author: Agent
    content: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the proposal to a dictionary format."""
        return {
            "author": self.author,
            "content": self.content,
        }


@dataclass(frozen=True)
class DeliberationResult:
    """Domain object representing the result of a peer council deliberation.
    
    Encapsulates a proposal with its validation checks and overall score.
    """
    
    proposal: Proposal
    checks: CheckSuiteResult
    score: float
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the deliberation result to a dictionary format."""
        return {
            "proposal": self.proposal.to_dict(),
            "checks": self.checks.to_dict(),
            "score": self.score,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeliberationResult:
        """Create a DeliberationResult from dictionary data."""
        # This is a simplified version - in a real implementation,
        # you'd need to properly reconstruct the Agent and CheckSuiteResult
        proposal_data = data["proposal"]
        proposal = Proposal(
            author=proposal_data["author"],  # This would need proper Agent reconstruction
            content=proposal_data["content"]
        )
        
        # For now, we'll create a simple CheckSuiteResult
        # In a real implementation, you'd reconstruct from the checks data
        checks = CheckSuiteResult(
            lint=None,  # Would be reconstructed from data["checks"]["lint"]
            dryrun=None,  # Would be reconstructed from data["checks"]["dryrun"] 
            policy=None,  # Would be reconstructed from data["checks"]["policy"]
        )
        
        return cls(
            proposal=proposal,
            checks=checks,
            score=data["score"]
        )
