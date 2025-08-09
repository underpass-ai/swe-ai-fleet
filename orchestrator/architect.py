from typing import Any, Dict, List

class ArchitectAgent:
    def select_best(self, proposals: List[str], telemetry: List[Dict[str, Any]], rubric: Dict[str, Any]) -> str:
        # Simple deterministic selection by the highest tool score; can be replaced by an LLM call.
        idx = 0
        if telemetry:
            scores = [1.0 if (t.get("dryrun", {}).get("ok") and t.get("lint", {}).get("ok")) else 0.0 for t in telemetry]
            idx = max(range(len(scores)), key=lambda i: scores[i])
        return proposals[idx]

class ArchitectSelector:
    def __init__(self, architect: ArchitectAgent) -> None:
        self._architect = architect

    def choose(self, ranked: List[Dict[str, Any]], rubric: Dict[str, Any]) -> Dict[str, Any]:
        top_k = ranked[: rubric.get("k", 3)]
        decision = self._architect.select_best(
            [t["proposal"]["content"] for t in top_k],
            [t["checks"] for t in top_k],
            rubric,
        )
        return {"winner": decision, "candidates": top_k}
