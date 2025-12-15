from typing import Any

import pytest

from core.orchestrator.config_module.role_config import RoleConfig
from core.orchestrator.config_module.system_config import SystemConfig
from core.orchestrator.domain.tasks.task_constraints import TaskConstraints
from core.orchestrator.domain.agents.services.architect_selector_service import ArchitectSelectorService
from core.orchestrator.usecases.peer_deliberation_usecase import Deliberate
from core.orchestrator.usecases.dispatch_usecase import Orchestrate


class TestOrchestrateUseCase:
    @pytest.mark.asyncio
    async def test_execute_routes_to_correct_council_and_architect(self, mocker) -> None:
        constraints = TaskConstraints(rubric={"k": 1}, architect_rubric={})
        council_result: list[dict[str, Any]] = [{"proposal": "A"}, {"proposal": "B"}]

        dev_council = mocker.Mock(spec=Deliberate)
        dev_council.execute = mocker.AsyncMock(return_value=council_result)

        qa_council = mocker.Mock(spec=Deliberate)
        qa_council.execute = mocker.AsyncMock(return_value=[{"proposal": "C"}])

        architect_result: dict[str, Any] = {"winner": "A", "candidates": council_result}
        architect = mocker.Mock(spec=ArchitectSelectorService)
        architect.choose.return_value = architect_result

        councils: dict[str, Deliberate] = {"DEV": dev_council, "QA": qa_council}
        system_config = SystemConfig(roles=[RoleConfig(name="DEV", replicas=1, model_profile="default")])
        orchestrate = Orchestrate(config=system_config, councils=councils, architect=architect)

        result = await orchestrate.execute(role="DEV", task="Implement feature", constraints=constraints)

        assert result is architect_result
        dev_council.execute.assert_awaited_once_with("Implement feature", constraints)
        qa_council.execute.assert_not_called()
        architect.choose.assert_called_once_with(council_result, constraints)

    @pytest.mark.asyncio
    async def test_execute_raises_when_role_not_configured(self, mocker) -> None:
        constraints = TaskConstraints(rubric={}, architect_rubric={})
        councils: dict[str, Deliberate] = {}
        architect = mocker.Mock(spec=ArchitectSelectorService)
        system_config = SystemConfig(roles=[])
        orchestrate = Orchestrate(config=system_config, councils=councils, architect=architect)

        with pytest.raises(KeyError):
            await orchestrate.execute(role="MISSING", task="Task", constraints=constraints)
