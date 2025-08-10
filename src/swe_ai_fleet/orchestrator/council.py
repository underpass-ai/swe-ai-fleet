from typing import Any


class Agent:
    def generate(self, task: str, constraints: dict[str, Any], diversity: bool) -> dict[str, Any]:
        raise NotImplementedError

    def critique(self, proposal: str, rubric: dict[str, Any]) -> str:
        raise NotImplementedError

    def revise(self, content: str, feedback: str) -> str:
        raise NotImplementedError


class Tooling:
    def kube_lint(self, manifest: str) -> dict[str, Any]:
        return {"ok": True, "issues": []}

    def kube_dryrun(self, manifest: str) -> dict[str, Any]:
        return {"ok": True, "errors": []}

    def opa_policy_check(self, manifest: str) -> dict[str, Any]:
        return {"ok": True, "violations": []}

    def score(self, checks: dict[str, Any]) -> float:
        score = 0.0
        score += 1.0 if checks["lint"]["ok"] else 0.0
        score += 1.0 if checks["dryrun"]["ok"] else 0.0
        score += 1.0 if checks["policy"]["ok"] else 0.0
        return score


class PeerCouncil:
    def __init__(self, agents: list[Agent], tooling: Tooling, rounds: int = 1) -> None:
        self._agents = agents
        self._tooling = tooling
        self._rounds = rounds

    def deliberate(self, task: str, constraints: dict[str, Any]) -> list[dict[str, Any]]:
        drafts: list[dict[str, Any]] = [
            {"author": a, "content": a.generate(task, constraints, diversity=True)["content"]}
            for a in self._agents
        ]

        for _ in range(self._rounds):
            for i, a in enumerate(self._agents):
                peer_idx = (i + 1) % len(drafts)
                feedback = a.critique(drafts[peer_idx]["content"], constraints.get("rubric", {}))
                revised = a.revise(drafts[peer_idx]["content"], feedback)
                drafts[peer_idx]["content"] = revised

        results: list[dict[str, Any]] = []
        for d in drafts:
            checks = {
                "lint": self._tooling.kube_lint(d["content"]),
                "dryrun": self._tooling.kube_dryrun(d["content"]),
                "policy": self._tooling.opa_policy_check(d["content"]),
            }
            results.append({"proposal": d, "checks": checks, "score": self._tooling.score(checks)})
        return sorted(results, key=lambda x: x["score"], reverse=True)
