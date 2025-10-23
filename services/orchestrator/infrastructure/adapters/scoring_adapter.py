"""Adapter for scoring operations."""

from __future__ import annotations

from typing import Any

from services.orchestrator.domain.ports import ScoringPort


class ScoringAdapter(ScoringPort):
    """Adapter implementing scoring using the Scoring service.
    
    This adapter implements the ScoringPort by delegating to the
    legacy Scoring infrastructure component.
    """
    
    def __init__(self):
        """Initialize the adapter.
        
        Imports Scoring at adapter creation time to avoid circular dependencies
        while only importing once.
        """
        # Import at adapter creation time (lazy but once)
        from core.orchestrator.domain.check_results.services.scoring import Scoring
        
        self._scoring = Scoring()
    
    def score(self, proposal: Any) -> float:
        """Score a proposal using the Scoring service.
        
        Args:
            proposal: Proposal to score
            
        Returns:
            Score value
        """
        return self._scoring.score(proposal)
    
    def validate(self, code: str) -> dict[str, Any]:
        """Validate code using the Scoring service.
        
        Args:
            code: Code to validate
            
        Returns:
            Validation results
        """
        return self._scoring.validate(code)
    
    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the wrapped Scoring instance.
        
        This allows the adapter to be used as a drop-in replacement
        for the Scoring class while maintaining the port interface.
        
        Args:
            name: Attribute name
            
        Returns:
            Attribute from wrapped Scoring instance
        """
        return getattr(self._scoring, name)

