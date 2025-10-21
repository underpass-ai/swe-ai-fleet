"""Value objects for deliberation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.orchestrator.domain.entities import CheckSuite


@dataclass(frozen=True)
class ProposalVO:
    """Value object representing a proposal.
    
    Immutable representation of an agent's proposal with metadata.
    
    Attributes:
        author_id: Unique identifier of the agent who created the proposal
        author_role: Role of the agent (e.g., "DEV", "QA", "ARCHITECT")
        content: The proposal content/text
        created_at_ms: Timestamp when proposal was created (milliseconds)
    """
    
    author_id: str
    author_role: str
    content: str
    created_at_ms: int
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "author_id": self.author_id,
            "author_role": self.author_role,
            "content": self.content,
            "created_at_ms": self.created_at_ms,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProposalVO:
        """Create from dictionary."""
        return cls(
            author_id=data["author_id"],
            author_role=data["author_role"],
            content=data["content"],
            created_at_ms=data["created_at_ms"],
        )


@dataclass(frozen=True)
class DeliberationResultVO:
    """Value object representing a deliberation result.
    
    Immutable representation of a deliberation result including
    the proposal, quality checks (as entity), and score.
    
    Attributes:
        proposal: The proposal that was deliberated
        checks: Quality check results (CheckSuite entity)
        score: Overall quality score
        rank: Ranking position in the deliberation
    """
    
    proposal: ProposalVO
    checks: CheckSuite  # Changed from CheckSuiteVO to CheckSuite entity
    score: float
    rank: int
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "proposal": self.proposal.to_dict(),
            "checks": self.checks.to_dict(),
            "score": self.score,
            "rank": self.rank,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeliberationResultVO:
        """Create from dictionary."""
        from services.orchestrator.domain.entities import CheckSuite
        
        return cls(
            proposal=ProposalVO.from_dict(data["proposal"]),
            checks=CheckSuite.from_dict(data["checks"]),
            score=data["score"],
            rank=data["rank"],
        )

