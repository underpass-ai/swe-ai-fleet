from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RoleContextPack:
    role: str
    case_header: dict[str, Any]
    plan_header: dict[str, Any]
    role_subtasks: list[dict[str, Any]] = field(default_factory=list)
    decisions_relevant: list[dict[str, Any]] = field(default_factory=list)
    decision_dependencies: list[dict[str, Any]] = field(default_factory=list)
    impacted_subtasks: list[dict[str, Any]] = field(default_factory=list)
    recent_milestones: list[dict[str, Any]] = field(default_factory=list)
    last_summary: str | None = None
    token_budget_hint: int = 8192  # hint for prompt packing

    # Allow dict-like access in consumer code/tests
    def __getitem__(self, key: str) -> Any:  # noqa: D401
        return getattr(self, key)
