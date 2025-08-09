from typing import Any, Dict, List

class Judge:
    def review(self, proposal: str, telemetry: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Placeholder: detect risky patterns; return simple risk score.
        risk = 0
        if "rm -rf /" in proposal:
            risk = 100
        return {"risk": risk, "notes": []}
