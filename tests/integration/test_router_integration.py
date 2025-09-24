from typing import Any

import pytest

from swe_ai_fleet.orchestrator.config_module import RoleConfig, SystemConfig
from swe_ai_fleet.orchestrator.domain import Task, TaskConstraints
from swe_ai_fleet.orchestrator.domain.agents.agent import Agent
from swe_ai_fleet.orchestrator.domain.agents.architect_agent import ArchitectAgent
from swe_ai_fleet.orchestrator.domain.agents.role import Role
from swe_ai_fleet.orchestrator.domain.agents.services import ArchitectSelectorService
from swe_ai_fleet.orchestrator.domain.check_results.services import Scoring
from swe_ai_fleet.orchestrator.usecases import Orchestrate
from swe_ai_fleet.orchestrator.usecases.peer_deliberation_usecase import Deliberate

pytestmark = pytest.mark.integration


class DummyAgent(Agent):
    def generate(self, task: str, constraints: TaskConstraints, diversity: bool) -> dict[str, Any]:
        return {"content": f"manifest for {task}\\nkind: Deployment"}

    def critique(self, proposal: str, rubric: dict[str, Any]) -> str:
        return "ok"

    def revise(self, content: str, feedback: str) -> str:
        return content


def test_router_dispatch_end_to_end_integration():
    tooling = Scoring()
    deliberation = Deliberate(agents=[DummyAgent()], tooling=tooling, rounds=1)
    architect = ArchitectSelectorService(architect=ArchitectAgent())
    cfg = SystemConfig(
        roles=[RoleConfig(name="devops", replicas=1, model_profile="devops")],
        require_human_approval=True,
    )
    router = Orchestrate(config=cfg, councils={"devops": deliberation}, architect=architect)

    role = Role.from_string("devops")
    task = Task.from_string("deploy web")
    constraints = TaskConstraints(
        rubric={},
        architect_rubric={"k": 1}
    )
    res = router.execute(role=role, task=task, constraints=constraints)
    assert "winner" in res and isinstance(res["winner"], str)
    assert "Deployment" in res["winner"]
    assert len(res["candidates"]) == 1
