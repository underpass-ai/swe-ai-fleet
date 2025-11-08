from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.context.domain.role_context_fields import RoleContextFields


@dataclass(frozen=True)
class ContextSection:
    """Represents a single section of context information.

    This domain object encapsulates a piece of context information
    that will be presented to agents, following DDD principles.
    """

    content: str
    section_type: str
    priority: int = 0  # Higher priority sections appear first

    def __str__(self) -> str:
        return self.content


@dataclass
class ContextSections:
    """A collection of context sections that form a complete context.

    This domain object manages the assembly of context sections,
    ensuring proper ordering and formatting for agent consumption.
    """

    sections: list[ContextSection] = field(default_factory=list)

    def add_section(self, content: str, section_type: str, priority: int = 0) -> None:
        """Add a new context section with specified priority."""
        section = ContextSection(content=content, section_type=section_type, priority=priority)
        self.sections.append(section)

    def add_case_identification(self, case_id: str, case_title: str) -> None:
        """Add case identification section with highest priority."""
        content = f"Case: {case_id} — {case_title}"
        self.add_section(content, "case_identification", priority=100)

    def add_plan_rationale(self, rationale: str) -> None:
        """Add plan rationale section."""
        content = f"Plan rationale: {rationale}"
        self.add_section(content, "plan_rationale", priority=90)

    def add_current_work_context(self, subtask_context_lines: list[str]) -> None:
        """Add current work context section."""
        for line in subtask_context_lines:
            self.add_section(line, "current_work", priority=80)

    def add_decision_context(self, decisions: list, max_decisions: int = 10) -> None:
        """Add decision context section with rationale for better agent understanding.

        Args:
            decisions: List of DecisionNode entities (NOT dicts)
            max_decisions: Maximum number of decisions to include
        """
        from core.reports.domain.decision_node import DecisionNode

        relevant_decisions = decisions[:max_decisions]

        if not relevant_decisions:
            return

        # Format decisions with title AND rationale for full context
        decision_lines = []
        for decision in relevant_decisions:
            # Type check (fail-fast if not DecisionNode)
            if not isinstance(decision, DecisionNode):
                raise TypeError(
                    f"Expected DecisionNode, got {type(decision).__name__}. "
                    f"context_sections.py must work with domain entities."
                )

            # Use domain types (NO defaults - fail if missing)
            title = decision.title
            rationale = decision.rationale
            status = decision.status.value  # Enum to string

            # Include rationale if available (key information for agents)
            if rationale:
                decision_lines.append(f"- {decision.id.to_string()}: {title} ({status})")
                decision_lines.append(f"  Rationale: {rationale}")
            else:
                decision_lines.append(f"- {decision.id.to_string()}: {title} ({status})")

        content = "Relevant decisions:\n" + "\n".join(decision_lines)
        self.add_section(content, "decision_context", priority=70)

    def add_historical_context(self, summary: str, max_length: int = 800) -> None:
        """Add historical context section."""
        truncated_summary = summary[:max_length]
        content = f"Last summary: {truncated_summary}"
        self.add_section(content, "historical_context", priority=60)

    def build_from_role_context_fields(
        self, role_context_fields: RoleContextFields, current_subtask_id: str | None = None
    ) -> None:
        """Build context sections from role context fields.

        This method inverts the control flow by having the domain object
        orchestrate the building of sections from the provided data.
        """
        # Case identification section (always present)
        self._build_case_identification_section(role_context_fields)

        # Plan context section (if rationale exists)
        if role_context_fields.plan_header.get("rationale"):
            self._build_plan_rationale_section(role_context_fields)

        # Current work context section (if subtask context exists)
        if self._has_current_subtask_context(role_context_fields, current_subtask_id):
            self._build_current_work_context_section(role_context_fields)

        # Decision context section (if decisions exist)
        if role_context_fields.decisions_relevant:
            self._build_decision_context_section(role_context_fields)

        # Historical context section (if summary exists)
        if role_context_fields.last_summary:
            self._build_historical_context_section(role_context_fields)

    def _build_case_identification_section(self, role_context_fields: RoleContextFields) -> None:
        """Build story identification section from role context fields."""
        story_id = role_context_fields.story_header.story_id.to_string()
        story_title = role_context_fields.story_header.title
        self.add_case_identification(story_id, story_title)

    def _build_plan_rationale_section(self, role_context_fields: RoleContextFields) -> None:
        """Build plan rationale section from role context fields."""
        rationale = role_context_fields.plan_header["rationale"]
        self.add_plan_rationale(rationale)

    def _build_current_work_context_section(self, role_context_fields: RoleContextFields) -> None:
        """Build current work context section from role context fields."""
        subtask_context_lines = role_context_fields.build_current_subtask_context_lines()
        self.add_current_work_context(subtask_context_lines)

    def _build_decision_context_section(self, role_context_fields: RoleContextFields) -> None:
        """Build decision context section from role context fields."""
        self.add_decision_context(role_context_fields.decisions_relevant)

    def _build_historical_context_section(self, role_context_fields: RoleContextFields) -> None:
        """Build historical context section from role context fields."""
        self.add_historical_context(role_context_fields.last_summary)

    def _has_current_subtask_context(
        self, role_context_fields: RoleContextFields, current_subtask_id: str | None
    ) -> bool:
        """Check if there's current subtask context to include."""
        return bool(role_context_fields.role_subtasks and current_subtask_id)

    def to_string(self) -> str:
        """Convert all sections to a formatted string.

        Sections are ordered by priority (highest first) and
        joined with newlines for readability.
        """
        sorted_sections = sorted(self.sections, key=lambda s: s.priority, reverse=True)
        return "\n".join(str(section) for section in sorted_sections)

    def is_empty(self) -> bool:
        """Check if there are no sections."""
        return len(self.sections) == 0

    def get_sections_by_type(self, section_type: str) -> list[ContextSection]:
        """Get all sections of a specific type."""
        return [section for section in self.sections if section.section_type == section_type]

    def clear(self) -> None:
        """Clear all sections."""
        self.sections.clear()
