from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RehydrationBundle:
    case_id: str
    generated_at_ms: int
    packs: dict[str, Any]  # role -> pack
    stats: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize bundle to a plain dict."""
        return {
            "case_id": self.case_id,
            "generated_at_ms": self.generated_at_ms,
            "packs": {
                role: {
                    "role": pack.role,
                    "case_header": pack.case_header,
                    "plan_header": pack.plan_header,
                    "role_subtasks": pack.role_subtasks,
                    "decisions_relevant": pack.decisions_relevant,
                    "decision_dependencies": pack.decision_dependencies,
                    "impacted_subtasks": pack.impacted_subtasks,
                    "recent_milestones": pack.recent_milestones,
                    "last_summary": pack.last_summary,
                    "token_budget_hint": pack.token_budget_hint,
                }
                for role, pack in self.packs.items()
            },
            "stats": self.stats,
        }
