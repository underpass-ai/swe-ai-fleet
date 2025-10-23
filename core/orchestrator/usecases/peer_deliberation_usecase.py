"""Peer deliberation use case."""


from typing import TYPE_CHECKING

from ..domain.agents.agent import Agent
from ..domain.check_results.services import Scoring
from ..domain.deliberation_result import DeliberationResult, Proposal

if TYPE_CHECKING:
    from ..domain.tasks.task_constraints import TaskConstraints


class Deliberate:
    """Use case for orchestrating peer deliberation on tasks.
    
    This use case coordinates the deliberation process between multiple agents,
    including proposal generation, peer review, and evaluation.
    """
    
    def __init__(self, agents: list[Agent], tooling: Scoring, rounds: int = 1) -> None:
        """Initialize the peer deliberation use case.
        
        Args:
            agents: List of agents participating in the deliberation
            tooling: Scoring tool for evaluating proposals
            rounds: Number of peer review rounds to perform
        """
        self._agents = agents
        self._tooling = tooling
        self._rounds = rounds

    async def execute(self, task: str, constraints: "TaskConstraints") -> list[DeliberationResult]:
        """Execute the peer deliberation process.
        
        Args:
            task: The task to deliberate on
            constraints: Constraints and rubric for the deliberation
            
        Returns:
            List of DeliberationResult objects, sorted by score (highest first)
        """
        # Create initial proposals from agents
        # Check if agent.generate is async or sync
        proposals: list[Proposal] = []
        for a in self._agents:
            result = a.generate(task, constraints, diversity=True)
            # If generate returns a coroutine, await it
            if hasattr(result, '__await__'):
                result = await result
            proposals.append(Proposal(
                author=a,
                content=result["content"]
            ))

        # Perform peer review rounds
        for _ in range(self._rounds):
            for i, a in enumerate(self._agents):
                peer_idx = (i + 1) % len(proposals)
                
                # Critique
                feedback = a.critique(proposals[peer_idx].content, constraints.get_rubric())
                if hasattr(feedback, '__await__'):
                    feedback = await feedback
                
                # Revise
                revised = a.revise(proposals[peer_idx].content, feedback)
                if hasattr(revised, '__await__'):
                    revised = await revised
                    
                proposals[peer_idx] = Proposal(
                    author=proposals[peer_idx].author,
                    content=revised
                )

        # Evaluate proposals and create deliberation results
        results: list[DeliberationResult] = []
        for proposal in proposals:
            check_suite = self._tooling.run_check_suite(proposal.content)
            score = self._tooling.score_checks(check_suite)
            results.append(DeliberationResult(
                proposal=proposal,
                checks=check_suite,
                score=score
            ))
        
        return sorted(results, key=lambda x: x.score, reverse=True)
