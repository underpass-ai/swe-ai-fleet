import math
from typing import Any

from core.orchestrator.domain.agents.agent import Agent
from core.orchestrator.domain.check_results import CheckSuiteResult, DryrunCheckResult, LintCheckResult, PolicyCheckResult
from core.orchestrator.domain.deliberation_result import DeliberationResult, Proposal


class MockAgent(Agent):
    def __init__(self, agent_id: str, role: str) -> None:
        self.agent_id = agent_id
        self.role = role

    def generate(self, task: str, constraints: Any, diversity: bool) -> dict[str, Any]:
        raise NotImplementedError

    def critique(self, proposal: str, rubric: dict[str, Any]) -> str:
        raise NotImplementedError

    def revise(self, content: str, feedback: str) -> str:
        raise NotImplementedError


class TestProposal:
    def test_to_dict_includes_author_and_content(self) -> None:
        agent = MockAgent(agent_id="agent-1", role="DEV")
        proposal = Proposal(author=agent, content="proposal content")

        as_dict = proposal.to_dict()

        assert as_dict["content"] == "proposal content"
        assert as_dict["author"]["agent_id"] == "agent-1"
        assert as_dict["author"]["role"] == "DEV"

    def test_to_dict_handles_none_author(self) -> None:
        proposal = Proposal(author=None, content="content")  # type: ignore[arg-type]

        as_dict = proposal.to_dict()

        assert as_dict["content"] == "content"
        assert as_dict["author"] is None


class TestDeliberationResult:
    def test_to_dict_includes_proposal_checks_and_score(self) -> None:
        agent = MockAgent(agent_id="agent-1", role="DEV")
        proposal = Proposal(author=agent, content="proposal")
        check_suite = CheckSuiteResult(
            lint=LintCheckResult.success(),
            dryrun=DryrunCheckResult.success(),
            policy=PolicyCheckResult.success(),
        )

        result = DeliberationResult(proposal=proposal, checks=check_suite, score=0.95)

        as_dict = result.to_dict()

        assert math.isclose(as_dict["score"], 0.95)
        assert as_dict["proposal"]["content"] == "proposal"
        assert "checks" in as_dict
