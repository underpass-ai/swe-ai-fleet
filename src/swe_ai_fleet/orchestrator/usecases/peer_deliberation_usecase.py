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

    def execute(self, task: str, constraints: "TaskConstraints") -> list[DeliberationResult]:
        """Execute the peer deliberation process.
        
        Args:
            task: The task to deliberate on
            constraints: Constraints and rubric for the deliberation
            
        Returns:
            List of DeliberationResult objects, sorted by score (highest first)
        """
        # Create initial proposals from agents
        proposals: list[Proposal] = [
            Proposal(
                author=a,
                content=a.generate(task, constraints, diversity=True)["content"]
            )
            for a in self._agents
        ]

        # Perform peer review rounds
        for _ in range(self._rounds):
            for i, a in enumerate(self._agents):
                peer_idx = (i + 1) % len(proposals)
                feedback = a.critique(proposals[peer_idx].content, constraints.get_rubric())
                revised = a.revise(proposals[peer_idx].content, feedback)
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
