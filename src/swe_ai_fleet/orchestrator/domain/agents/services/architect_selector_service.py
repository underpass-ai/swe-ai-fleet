"""Architect selector domain service."""

from typing import TYPE_CHECKING, Any

from ...agents.architect_agent import ArchitectAgent
from ...deliberation_result import DeliberationResult

if TYPE_CHECKING:
    from ...tasks.task_constraints import TaskConstraints


class ArchitectSelectorService:
    """Domain service for selecting the best architect proposal.
    
    This service orchestrates the selection process by coordinating
    between ranked proposals, rubrics, and architect agents.
    """
    
    def __init__(self, architect: ArchitectAgent) -> None:
        """Initialize the selector service with an architect agent.
        
        Args:
            architect: The architect agent to use for selection
        """
        self._architect = architect

    def choose(self, ranked: list[DeliberationResult], constraints: "TaskConstraints") -> dict[str, Any]:
        """Choose the best proposal from ranked candidates.
        
        Args:
            ranked: List of ranked deliberation result candidates
            constraints: Task constraints containing selection criteria
            
        Returns:
            Dictionary containing the winner (DeliberationResult) and all candidates (list of dicts)
        """
        k = constraints.get_k_value()
        top_k = ranked[:k]
        
        # Convert DeliberationResult objects to the format expected by architect
        proposals = [result.proposal.content for result in top_k]
        checks = [result.checks.to_dict() for result in top_k]
        
        winning_content = self._architect.select_best(
            proposals,
            checks,
            constraints.get_architect_rubric(),
        )
        
        # Find the DeliberationResult that matches the winning content
        winner = next(
            (result for result in top_k if result.proposal.content == winning_content),
            top_k[0]  # Fallback to first if no match (shouldn't happen)
        )
        
        return {"winner": winner, "candidates": [result.to_dict() for result in top_k]}
