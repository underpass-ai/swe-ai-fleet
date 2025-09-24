from typing import Any

from swe_ai_fleet.orchestrator.domain.agents.agent import Agent
from swe_ai_fleet.orchestrator.domain.check_results.services import Scoring
from swe_ai_fleet.orchestrator.domain.tasks.task_constraints import TaskConstraints
from swe_ai_fleet.orchestrator.usecases.peer_deliberation_usecase import Deliberate


class AgentA(Agent):
    def generate(self, task: str, constraints: TaskConstraints, diversity: bool) -> dict[str, Any]:
        return {"content": f"A:{task}"}

    def critique(self, proposal: str, rubric: dict[str, Any]) -> str:
        return "ok"

    def revise(self, content: str, feedback: str) -> str:
        return content + "|revA"


class AgentB(Agent):
    def generate(self, task: str, constraints: TaskConstraints, diversity: bool) -> dict[str, Any]:
        return {"content": f"B:{task}"}

    def critique(self, proposal: str, rubric: dict[str, Any]) -> str:
        return "ok"

    def revise(self, content: str, feedback: str) -> str:
        return content + "|revB"


def test_peer_council_deliberation_ranks_and_scores():
    deliberation = Deliberate(agents=[AgentA(), AgentB()], tooling=Scoring(), rounds=1)
    constraints = TaskConstraints(rubric={}, architect_rubric={})
    ranked = deliberation.execute("deploy service-x", constraints)

    assert isinstance(ranked, list) and len(ranked) == 2
    for r in ranked:
        assert hasattr(r, 'proposal') and hasattr(r, 'checks') and hasattr(r, 'score')
        assert isinstance(r.score, float) and r.score >= 0.0
        # ensure revise cycle left a trace
        assert "|rev" in r.proposal.content
