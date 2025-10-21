"""Port for scoring/tooling operations."""

from __future__ import annotations

from typing import Any, Protocol


class ScoringPort(Protocol):
    """Port for scoring and validation operations.
    
    This port defines the interface for scoring proposals and validating
    code changes, abstracting the infrastructure details of how scoring
    is performed.
    
    Implementations might use:
    - Policy-based scoring
    - Linting
    - Dry-run validation
    - AI-based scoring
    """
    
    def score(self, proposal: Any) -> float:
        """Score a proposal.
        
        Args:
            proposal: Proposal to score
            
        Returns:
            Score value (typically 0.0 to 1.0)
        """
        ...
    
    def validate(self, code: str) -> dict[str, Any]:
        """Validate code changes.
        
        Args:
            code: Code to validate
            
        Returns:
            Validation results
        """
        ...

