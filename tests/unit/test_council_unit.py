from typing import Any, Dict
from edgecrew.orchestrator.council import PeerCouncil, Tooling, Agent


class AgentA(Agent):
    def generate(self, task: str, constraints: Dict[str, Any], diversity: bool) -> Dict[str, Any]:
        return {"content": f"A:{task}"}

    def critique(self, proposal: str, rubric: Dict[str, Any]) -> str:
        return "ok"

    def revise(self, content: str, feedback: str) -> str:
        return content + "|revA"


class AgentB(Agent):
    def generate(self, task: str, constraints: Dict[str, Any], diversity: bool) -> Dict[str, Any]:
        return {"content": f"B:{task}"}

    def critique(self, proposal: str, rubric: Dict[str, Any]) -> str:
        return "ok"

    def revise(self, content: str, feedback: str) -> str:
        return content + "|revB"


def test_peer_council_deliberation_ranks_and_scores():
    council = PeerCouncil(
        agents=[AgentA(), AgentB()], tooling=Tooling(), rounds=1)
    ranked = council.deliberate("deploy service-x", constraints={"rubric": {}})

    assert isinstance(ranked, list) and len(ranked) == 2
    for r in ranked:
        assert "proposal" in r and "checks" in r and "score" in r
        assert isinstance(r["score"], float) and r["score"] >= 0.0
        # ensure revise cycle left a trace
        assert "|rev" in r["proposal"]["content"]
