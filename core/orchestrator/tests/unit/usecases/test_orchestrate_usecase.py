from typing import Any

import pytest

from core.orchestrator.config_module.role_config import RoleConfig
from core.orchestrator.config_module.system_config import SystemConfig
from core.orchestrator.domain.agents.role import Role
from core.orchestrator.domain.agents.services.architect_selector_service import ArchitectSelectorService
from core.orchestrator.domain.deliberation_result import DeliberationResult, Proposal
from core.orchestrator.domain.tasks.task import Task
from core.orchestrator.domain.tasks.task_constraints import TaskConstraints
from core.orchestrator.domain.agents.agent import Agent
from core.orchestrator.usecases.orchestrate_usecase import Orchestrate
from core.orchestrator.usecases.peer_deliberation_usecase import Deliberate


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


class TestOrchestrateUseCase:
    @pytest.mark.asyncio
    async def test_execute_routes_to_council_and_architect(self, mocker) -> None:
        constraints = TaskConstraints(rubric={}, architect_rubric={})
        task = Task(description="Implement feature", id="task-1")
        role = Role(name="DEV")

        agent = MockAgent(agent_id="agent-1", role="DEV")
        proposal = Proposal(author=agent, content="proposal-content")
        deliberation_result = DeliberationResult(
            proposal=proposal,
            checks=mocker.Mock(),
            score=1.0,
        )

        council = mocker.Mock(spec=Deliberate)
        council.execute = mocker.AsyncMock(return_value=[deliberation_result])

        architect_result: dict[str, Any] = {"winner": deliberation_result, "candidates": []}
        architect = mocker.Mock(spec=ArchitectSelectorService)
        architect.choose.return_value = architect_result

        councils: dict[str, Deliberate] = {"DEV": council}
        system_config = SystemConfig(roles=[RoleConfig(name="DEV", replicas=1, model_profile="default")])
        usecase = Orchestrate(config=system_config, councils=councils, architect=architect)

        result = await usecase.execute(role=role, task=task, constraints=constraints)

        assert result is architect_result
        council.execute.assert_awaited_once_with("Implement feature", constraints)
        architect.choose.assert_called_once_with([deliberation_result], constraints)

    @pytest.mark.asyncio
    async def test_execute_raises_when_role_not_configured(self, mocker) -> None:
        constraints = TaskConstraints(rubric={}, architect_rubric={})
        task = Task(description="Task", id="task-1")
        role = Role(name="MISSING")

        councils: dict[str, Deliberate] = {}
        architect = mocker.Mock(spec=ArchitectSelectorService)
        system_config = SystemConfig(roles=[])
        usecase = Orchestrate(config=system_config, councils=councils, architect=architect)

        with pytest.raises(KeyError):
            await usecase.execute(role=role, task=task, constraints=constraints)
