from typing import Any

import pytest

from services.orchestrator.application.usecases.create_council_usecase import (
    CouncilCreationResult,
    CreateCouncilUseCase,
)
from services.orchestrator.domain.entities import CouncilRegistry


class MockAgent:
    def __init__(self, agent_id: str, role: str) -> None:
        self.agent_id = agent_id
        self.role = role


class MockAgentCollection:
    def __init__(self) -> None:
        self._agents: list[MockAgent] = []
        self._is_empty = False

    def create_and_add_agents(
        self,
        role: str,
        num_agents: int,
        vllm_config: Any,
        agent_factory: Any,
        custom_params: dict | None = None,
    ) -> None:
        for i in range(num_agents):
            self._agents.append(MockAgent(agent_id=f"{role}-{i+1}", role=role))

    @property
    def is_empty(self) -> bool:
        return self._is_empty

    @property
    def count(self) -> int:
        return len(self._agents)

    def get_all_agents(self) -> list[MockAgent]:
        return self._agents

    def get_all_ids(self) -> list[str]:
        return [agent.agent_id for agent in self._agents]


class TestCreateCouncilUseCase:
    def test_execute_creates_council_and_registers_it(self, mocker) -> None:
        registry = CouncilRegistry()
        use_case = CreateCouncilUseCase(council_registry=registry)

        mock_agent_collection = MockAgentCollection()
        mock_council = mocker.MagicMock()
        mock_scoring = mocker.MagicMock()
        mock_vllm_config = mocker.MagicMock()

        def mock_agent_factory(*args: Any, **kwargs: Any) -> MockAgent:
            return MockAgent(agent_id="agent-1", role="DEV")

        def mock_council_factory(agents: list[Any], tooling: Any, rounds: int) -> Any:
            return mock_council

        mocker.patch(
            "services.orchestrator.application.usecases.create_council_usecase.AgentCollection",
            return_value=mock_agent_collection,
        )

        result = use_case.execute(
            role="DEV",
            num_agents=3,
            vllm_config=mock_vllm_config,
            agent_factory=mock_agent_factory,
            council_factory=mock_council_factory,
            scoring_tool=mock_scoring,
            agent_type_str="RAY_VLLM",
        )

        assert isinstance(result, CouncilCreationResult)
        assert result.council_id == "council-dev"
        assert result.agents_created == 3
        assert len(result.agent_ids) == 3
        assert result.council is mock_council
        assert registry.has_council("DEV")

    def test_execute_raises_when_role_empty(self, mocker) -> None:
        registry = CouncilRegistry()
        use_case = CreateCouncilUseCase(council_registry=registry)

        with pytest.raises(ValueError, match="Role cannot be empty"):
            use_case.execute(
                role="",
                num_agents=3,
                vllm_config=mocker.MagicMock(),
                agent_factory=lambda: None,
                council_factory=lambda *args: None,
                scoring_tool=mocker.MagicMock(),
            )

    def test_execute_raises_when_num_agents_zero(self, mocker) -> None:
        registry = CouncilRegistry()
        use_case = CreateCouncilUseCase(council_registry=registry)

        with pytest.raises(ValueError, match="num_agents must be positive"):
            use_case.execute(
                role="DEV",
                num_agents=0,
                vllm_config=mocker.MagicMock(),
                agent_factory=lambda: None,
                council_factory=lambda *args: None,
                scoring_tool=mocker.MagicMock(),
            )

    def test_execute_raises_when_council_already_exists(self, mocker) -> None:
        registry = CouncilRegistry()
        use_case = CreateCouncilUseCase(council_registry=registry)

        mock_council = mocker.MagicMock()
        registry.register_council(role="DEV", council=mock_council, agents=[])

        with pytest.raises(ValueError, match="already exists"):
            use_case.execute(
                role="DEV",
                num_agents=3,
                vllm_config=mocker.MagicMock(),
                agent_factory=lambda: None,
                council_factory=lambda *args: None,
                scoring_tool=mocker.MagicMock(),
            )

    def test_execute_raises_when_agent_type_invalid(self, mocker) -> None:
        registry = CouncilRegistry()
        use_case = CreateCouncilUseCase(council_registry=registry)

        with pytest.raises(ValueError):
            use_case.execute(
                role="DEV",
                num_agents=3,
                vllm_config=mocker.MagicMock(),
                agent_factory=lambda: None,
                council_factory=lambda *args: None,
                scoring_tool=mocker.MagicMock(),
                agent_type_str="INVALID",
            )

    def test_execute_raises_when_agent_collection_empty(self, mocker) -> None:
        registry = CouncilRegistry()
        use_case = CreateCouncilUseCase(council_registry=registry)

        mock_empty_collection = MockAgentCollection()
        mock_empty_collection._is_empty = True

        mocker.patch(
            "services.orchestrator.application.usecases.create_council_usecase.AgentCollection",
            return_value=mock_empty_collection,
        )

        with pytest.raises(RuntimeError, match="AgentCollection is empty"):
            use_case.execute(
                role="DEV",
                num_agents=3,
                vllm_config=mocker.MagicMock(),
                agent_factory=lambda: None,
                council_factory=lambda *args: None,
                scoring_tool=mocker.MagicMock(),
            )
