from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RoleContextFields:
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
    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def filter_role_subtasks_by_id(
        self,
        subtask_id: str,
    ) -> list[dict[str, Any]]:
        """Return role_subtasks filtered to a specific subtask id."""
        return [s for s in self.role_subtasks if s.get("subtask_id") == subtask_id]

    def detect_scopes(self) -> set[str]:
        """Infer available prompt scopes from the current pack contents."""
        scopes: set[str] = set()
        if self.case_header:
            scopes.add("CASE_HEADER")
        if self.plan_header:
            scopes.add("PLAN_HEADER")
        if self.decisions_relevant:
            scopes.add("DECISIONS_RELEVANT_ROLE")
        if self.decision_dependencies:
            scopes.add("DEPS_RELEVANT")
        if self.impacted_subtasks:
            scopes.add("SUBTASKS_ROLE")
        if self.role_subtasks and len(self.role_subtasks) > 5:
            scopes.add("SUBTASKS_ROLE_MIN")
        if self.recent_milestones:
            scopes.add("MILESTONES")
        if self.last_summary:
            scopes.add("SUMMARY_LAST")
        # Architect/QA heuristics
        if self.role in {"architect", "qa"}:
            scopes.discard("DECISIONS_RELEVANT_ROLE")
            scopes.add("DECISIONS_GLOBAL")
            if "SUBTASKS_ROLE" in scopes:
                scopes.add("SUBTASKS_ALL_MIN")
        return scopes

    def get_recent_milestones(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return the last ``limit`` recent milestones.

        When ``limit`` is non-positive, an empty list is returned.
        """
        if limit <= 0:
            return []
        return self.recent_milestones[-limit:]

    def filter_impacted_subtasks_by_id(
        self,
        subtask_id: str,
    ) -> list[dict[str, Any]]:
        """Return impacted_subtasks filtered to a specific subtask id."""
        return [item for item in self.impacted_subtasks if item.get("subtask_id") == subtask_id]

    def build_current_subtask_context_lines(self) -> list[str]:
        """Compose context lines for the current subtask if available.

        Assumes the pack was previously narrowed to the target subtask, so the
        first element of ``role_subtasks`` represents the current one.
        """
        lines: list[str] = []
        if self.role_subtasks:
            subtask = self.role_subtasks[0]
            subtask_id = subtask.get("subtask_id")
            title = subtask.get("title")
            if subtask_id and title:
                lines.append(f"Current subtask: {subtask_id} — {title}")
            depends_on = subtask.get("depends_on") or []
            if depends_on:
                lines.append("Depends on: " + ", ".join(depends_on))
        return lines
