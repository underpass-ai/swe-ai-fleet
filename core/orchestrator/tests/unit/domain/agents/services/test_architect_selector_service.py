from typing import Any

from core.orchestrator.domain.agents.agent import Agent
from core.orchestrator.domain.agents.architect_agent import ArchitectAgent
from core.orchestrator.domain.agents.services.architect_selector_service import ArchitectSelectorService
from core.orchestrator.domain.check_results import CheckSuiteResult, DryrunCheckResult, LintCheckResult, PolicyCheckResult
from core.orchestrator.domain.deliberation_result import DeliberationResult, Proposal
from core.orchestrator.domain.tasks.task_constraints import TaskConstraints


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


class TestArchitectSelectorService:
    def test_choose_selects_top_k_and_returns_winner(self) -> None:
        architect = ArchitectAgent()
        service = ArchitectSelectorService(architect=architect)

        agent1 = MockAgent(agent_id="agent-1", role="DEV")
        agent2 = MockAgent(agent_id="agent-2", role="DEV")
        agent3 = MockAgent(agent_id="agent-3", role="DEV")

        check_suite_high = CheckSuiteResult(
            lint=LintCheckResult.success(),
            dryrun=DryrunCheckResult.success(),
            policy=PolicyCheckResult.success(),
        )
        check_suite_low = CheckSuiteResult(
            lint=LintCheckResult.failure(["issue"]),
            dryrun=DryrunCheckResult.success(),
            policy=PolicyCheckResult.success(),
        )

        ranked = [
            DeliberationResult(
                proposal=Proposal(author=agent1, content="proposal-1"),
                checks=check_suite_high,
                score=1.0,
            ),
            DeliberationResult(
                proposal=Proposal(author=agent2, content="proposal-2"),
                checks=check_suite_low,
                score=0.67,
            ),
            DeliberationResult(
                proposal=Proposal(author=agent3, content="proposal-3"),
                checks=check_suite_low,
                score=0.5,
            ),
        ]

        constraints = TaskConstraints(rubric={}, architect_rubric={"k": 2})

        result = service.choose(ranked=ranked, constraints=constraints)

        assert "winner" in result
        assert "candidates" in result
        assert len(result["candidates"]) == 2
        assert result["winner"].proposal.content in ["proposal-1", "proposal-2"]

    def test_choose_uses_default_k_when_not_specified(self) -> None:
        architect = ArchitectAgent()
        service = ArchitectSelectorService(architect=architect)

        agent = MockAgent(agent_id="agent-1", role="DEV")
        check_suite = CheckSuiteResult(
            lint=LintCheckResult.success(),
            dryrun=DryrunCheckResult.success(),
            policy=PolicyCheckResult.success(),
        )

        ranked = [
            DeliberationResult(
                proposal=Proposal(author=agent, content=f"proposal-{i}"),
                checks=check_suite,
                score=1.0 - i * 0.1,
            )
            for i in range(5)
        ]

        constraints = TaskConstraints(rubric={}, architect_rubric={})

        result = service.choose(ranked=ranked, constraints=constraints)

        assert len(result["candidates"]) == 3

    def test_choose_fallback_to_first_if_no_match(self) -> None:
        architect = ArchitectAgent()
        service = ArchitectSelectorService(architect=architect)

        agent = MockAgent(agent_id="agent-1", role="DEV")
        check_suite = CheckSuiteResult(
            lint=LintCheckResult.success(),
            dryrun=DryrunCheckResult.success(),
            policy=PolicyCheckResult.success(),
        )

        ranked = [
            DeliberationResult(
                proposal=Proposal(author=agent, content="proposal-1"),
                checks=check_suite,
                score=1.0,
            ),
        ]

        constraints = TaskConstraints(rubric={}, architect_rubric={"k": 1})

        result = service.choose(ranked=ranked, constraints=constraints)

        assert result["winner"].proposal.content == "proposal-1"
