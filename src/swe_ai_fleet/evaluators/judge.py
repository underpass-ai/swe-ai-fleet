from typing import Any


class Judge:
    def review(self, proposal: str, telemetry: list[dict[str, Any]]) -> dict[str, Any]:
        # Placeholder: detect risky patterns; return simple risk score.
        risk = 0
        if "rm -rf /" in proposal:
            risk = 100
        return {"risk": risk, "notes": []}
