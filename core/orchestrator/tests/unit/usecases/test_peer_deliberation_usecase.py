import math
from typing import Any

import pytest

from core.orchestrator.domain.agents.agent import Agent
from core.orchestrator.domain.check_results import CheckSuiteResult, DryrunCheckResult, LintCheckResult, PolicyCheckResult
from core.orchestrator.domain.check_results.services.scoring import Scoring
from core.orchestrator.domain.deliberation_result import DeliberationResult, Proposal
from core.orchestrator.domain.tasks.task_constraints import TaskConstraints
from core.orchestrator.usecases.peer_deliberation_usecase import Deliberate


class MockAgent(Agent):
    def __init__(self, agent_id: str, role: str) -> None:
        self.agent_id = agent_id
        self.role = role
        self.generate_calls: list[tuple[str, TaskConstraints, bool]] = []
        self.critique_calls: list[tuple[str, dict[str, Any]]] = []
        self.revise_calls: list[tuple[str, str]] = []

    def generate(self, task: str, constraints: TaskConstraints, diversity: bool) -> dict[str, Any]:
        self.generate_calls.append((task, constraints, diversity))
        return {"content": f"Proposal from {self.agent_id} for {task}"}

    def critique(self, proposal: str, rubric: dict[str, Any]) -> str:
        self.critique_calls.append((proposal, rubric))
        return f"Feedback on {proposal[:20]}"

    def revise(self, content: str, feedback: str) -> str:
        self.revise_calls.append((content, feedback))
        return f"Revised: {content}"


class AsyncMockAgent(Agent):
    def __init__(self, agent_id: str, role: str) -> None:
        self.agent_id = agent_id
        self.role = role
        self.generate_calls: list[tuple[str, TaskConstraints, bool]] = []
        self.critique_calls: list[tuple[str, dict[str, Any]]] = []
        self.revise_calls: list[tuple[str, str]] = []

    async def generate(self, task: str, constraints: TaskConstraints, diversity: bool) -> dict[str, Any]:  # type: ignore[override]
        self.generate_calls.append((task, constraints, diversity))
        return {"content": f"Proposal from {self.agent_id} for {task}"}

    async def critique(self, proposal: str, rubric: dict[str, Any]) -> str:  # type: ignore[override]
        self.critique_calls.append((proposal, rubric))
        return f"Feedback on {proposal[:20]}"

    async def revise(self, content: str, feedback: str) -> str:  # type: ignore[override]
        self.revise_calls.append((content, feedback))
        return f"Revised: {content}"


class TestDeliberateUseCase:
    @pytest.mark.asyncio
    async def test_execute_with_sync_agents_creates_proposals_and_scores(self, mocker) -> None:
        agent1 = MockAgent(agent_id="agent-1", role="DEV")
        agent2 = MockAgent(agent_id="agent-2", role="DEV")
        scoring = Scoring()
        constraints = TaskConstraints(rubric={"k": 1}, architect_rubric={})

        usecase = Deliberate(agents=[agent1, agent2], tooling=scoring, rounds=1)

        results = await usecase.execute(task="Implement feature", constraints=constraints)

        assert len(results) == 2
        assert all(isinstance(r, DeliberationResult) for r in results)
        assert all(r.score >= 0.0 and r.score <= 1.0 for r in results)
        assert results == sorted(results, key=lambda x: x.score, reverse=True)

        assert len(agent1.generate_calls) == 1
        assert agent1.generate_calls[0][0] == "Implement feature"
        assert agent1.generate_calls[0][2] is True

    @pytest.mark.asyncio
    async def test_execute_with_async_agents_awaits_coroutines(self, mocker) -> None:
        agent1 = AsyncMockAgent(agent_id="agent-1", role="DEV")
        agent2 = AsyncMockAgent(agent_id="agent-2", role="DEV")
        scoring = Scoring()
        constraints = TaskConstraints(rubric={}, architect_rubric={})

        usecase = Deliberate(agents=[agent1, agent2], tooling=scoring, rounds=1)

        results = await usecase.execute(task="Test task", constraints=constraints)

        assert len(results) == 2
        assert len(agent1.generate_calls) == 1

    @pytest.mark.asyncio
    async def test_execute_performs_peer_review_rounds(self, mocker) -> None:
        agent1 = MockAgent(agent_id="agent-1", role="DEV")
        agent2 = MockAgent(agent_id="agent-2", role="DEV")
        scoring = Scoring()
        constraints = TaskConstraints(rubric={"criteria": "quality"}, architect_rubric={})

        usecase = Deliberate(agents=[agent1, agent2], tooling=scoring, rounds=2)

        results = await usecase.execute(task="Review task", constraints=constraints)

        assert len(results) == 2
        assert len(agent1.critique_calls) == 2
        assert len(agent1.revise_calls) == 2
        assert len(agent2.critique_calls) == 2
        assert len(agent2.revise_calls) == 2

        for critique_call in agent1.critique_calls:
            assert critique_call[1] == constraints.get_rubric()

    @pytest.mark.asyncio
    async def test_execute_peer_review_rotates_through_agents(self, mocker) -> None:
        agent1 = MockAgent(agent_id="agent-1", role="DEV")
        agent2 = MockAgent(agent_id="agent-2", role="DEV")
        agent3 = MockAgent(agent_id="agent-3", role="DEV")
        scoring = Scoring()
        constraints = TaskConstraints(rubric={}, architect_rubric={})

        usecase = Deliberate(agents=[agent1, agent2, agent3], tooling=scoring, rounds=1)

        await usecase.execute(task="Task", constraints=constraints)

        assert len(agent1.critique_calls) == 1
        assert len(agent2.critique_calls) == 1
        assert len(agent3.critique_calls) == 1

    @pytest.mark.asyncio
    async def test_execute_returns_results_sorted_by_score_descending(self, mocker) -> None:
        agent1 = MockAgent(agent_id="agent-1", role="DEV")
        agent2 = MockAgent(agent_id="agent-2", role="DEV")

        scoring = mocker.Mock(spec=Scoring)
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
        scoring.run_check_suite.side_effect = [check_suite_high, check_suite_low]
        scoring.score_checks.side_effect = [1.0, 0.67]

        constraints = TaskConstraints(rubric={}, architect_rubric={})
        usecase = Deliberate(agents=[agent1, agent2], tooling=scoring, rounds=0)

        results = await usecase.execute(task="Task", constraints=constraints)

        assert len(results) == 2
        assert math.isclose(results[0].score, 1.0)
        assert math.isclose(results[1].score, 0.67)
