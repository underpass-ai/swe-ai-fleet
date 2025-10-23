from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CaseSpecDTO:
    case_id: str
    title: str
    description: str
    acceptance_criteria: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    requester_id: str = ""
    tags: list[str] = field(default_factory=list)
    created_at_ms: int = 0


@dataclass(frozen=True)
class SubtaskPlanDTO:
    subtask_id: str
    title: str
    description: str
    role: str
    suggested_tech: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    estimate_points: float = 0.0
    priority: int = 0
    risk_score: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize subtask plan to a plain dict."""
        return {
            "subtask_id": self.subtask_id,
            "title": self.title,
            "description": self.description,
            "role": self.role,
            "depends_on": list(self.depends_on or []),
            "estimate_points": float(self.estimate_points),
            "priority": int(self.priority),
            "risk_score": float(self.risk_score),
            "suggested_tech": list(self.suggested_tech or []),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class PlanVersionDTO:
    plan_id: str
    case_id: str
    version: int
    status: str
    author_id: str
    rationale: str = ""
    subtasks: list[SubtaskPlanDTO] = field(default_factory=list)
    created_at_ms: int = 0


@dataclass(frozen=True)
class PlanningEventDTO:
    id: str
    event: str
    actor: str
    payload: dict[str, Any]
    ts_ms: int
