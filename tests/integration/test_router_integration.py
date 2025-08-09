from typing import Any

import pytest

from edgecrew.orchestrator.architect import ArchitectAgent, ArchitectSelector
from edgecrew.orchestrator.config import RoleConfig, SystemConfig
from edgecrew.orchestrator.council import Agent, PeerCouncil, Tooling
from edgecrew.orchestrator.router import Router

pytestmark = pytest.mark.integration


class DummyAgent(Agent):
    def generate(self, task: str, constraints: dict[str, Any], diversity: bool) -> dict[str, Any]:
        return {"content": f"manifest for {task}\\nkind: Deployment"}

    def critique(self, proposal: str, rubric: dict[str, Any]) -> str:
        return "ok"

    def revise(self, content: str, feedback: str) -> str:
        return content


def test_router_dispatch_end_to_end_integration():
    tooling = Tooling()
    council = PeerCouncil(agents=[DummyAgent()], tooling=tooling, rounds=1)
    architect = ArchitectSelector(architect=ArchitectAgent())
    cfg = SystemConfig(
        roles=[RoleConfig(name="devops", replicas=1, model_profile="devops")],
        require_human_approval=True,
    )
    router = Router(config=cfg, councils={"devops": council}, architect=architect)

    res = router.dispatch(
        role="devops", task="deploy web", constraints={"architect_rubric": {"k": 1}}
    )
    assert "winner" in res and isinstance(res["winner"], str)
    assert "Deployment" in res["winner"]
    assert len(res["candidates"]) == 1
