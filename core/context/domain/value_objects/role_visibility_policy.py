"""RoleVisibilityPolicy Value Object - Encapsulates visibility rules for a role."""

from dataclasses import dataclass
from enum import Enum

from core.context.domain.role import Role


class VisibilityScope(str, Enum):
    """Scope of data visibility for a role."""

    ALL = "all"                    # See everything
    ASSIGNED = "assigned"          # Only assigned to role/user
    EPIC_CHILDREN = "epic_children"  # All within assigned epics
    STORY_CHILDREN = "story_children"  # All within assigned stories
    STORY_SCOPED = "story_scoped"  # Scoped to specific stories
    TESTING_PHASE = "testing_phase"  # Stories in testing
    TESTING_TASKS = "testing_tasks"  # Only testing tasks
    QUALITY_RELATED = "quality_related"  # QA/quality decisions
    NONE = "none"                  # No visibility


@dataclass(frozen=True)
class EntityVisibilityRule:
    """Visibility rule for a specific entity type.

    Defines what data a role can see for an entity (Epic, Story, Task, etc.).
    """

    scope: VisibilityScope
    filter_by: str  # Field name to filter by (e.g., "assigned_to", "epic_id")
    additional_filters: dict[str, list[str]]  # Extra filters (e.g., status, type)

    def __post_init__(self) -> None:
        """Validate visibility rule."""
        if self.scope != VisibilityScope.NONE and self.scope != VisibilityScope.ALL:
            if not self.filter_by:
                raise ValueError(
                    f"filter_by is required for scope {self.scope.value}. "
                    f"Specify field name to filter by."
                )

    def allows_all_access(self) -> bool:
        """Check if this rule allows access to all entities."""
        return self.scope == VisibilityScope.ALL

    def denies_all_access(self) -> bool:
        """Check if this rule denies all access."""
        return self.scope == VisibilityScope.NONE


@dataclass(frozen=True)
class RoleVisibilityPolicy:
    """Visibility policy for a specific role.

    Encapsulates all visibility rules for what data a role can access.
    This is the domain representation of config/context_visibility.yaml.

    Domain Invariant: Rules must be consistent (no contradictions).
    Immutable by design (frozen=True).
    """

    role: Role
    epic_rule: EntityVisibilityRule
    story_rule: EntityVisibilityRule
    task_rule: EntityVisibilityRule
    decision_rule: EntityVisibilityRule
    plan_rule: EntityVisibilityRule
    milestone_rule: EntityVisibilityRule
    summary_rule: EntityVisibilityRule

    def __post_init__(self) -> None:
        """Validate policy consistency.

        Raises:
            ValueError: If policy has contradictions
        """
        # If role has no epic access, epic_children scope doesn't make sense
        if self.epic_rule.denies_all_access():
            if self.story_rule.scope == VisibilityScope.EPIC_CHILDREN:
                raise ValueError(
                    f"Inconsistent policy for {self.role.value}: "
                    f"Cannot have story scope=epic_children when epic access is none"
                )

        # If role has no story access, story_children scope doesn't make sense
        if self.story_rule.denies_all_access():
            if self.task_rule.scope == VisibilityScope.STORY_CHILDREN:
                raise ValueError(
                    f"Inconsistent policy for {self.role.value}: "
                    f"Cannot have task scope=story_children when story access is none"
                )

    def can_access_epics(self) -> bool:
        """Check if role can access any epics."""
        return not self.epic_rule.denies_all_access()

    def can_access_stories(self) -> bool:
        """Check if role can access any stories."""
        return not self.story_rule.denies_all_access()

    def can_access_tasks(self) -> bool:
        """Check if role can access any tasks."""
        return not self.task_rule.denies_all_access()

    def has_full_access(self) -> bool:
        """Check if role has full access to all data (e.g., Product Owner)."""
        return (
            self.epic_rule.allows_all_access()
            and self.story_rule.allows_all_access()
            and self.task_rule.allows_all_access()
            and self.decision_rule.allows_all_access()
        )

    def is_epic_scoped(self) -> bool:
        """Check if role's primary scope is epic-level (e.g., Architect)."""
        return (
            self.epic_rule.scope == VisibilityScope.ASSIGNED
            and self.story_rule.scope == VisibilityScope.EPIC_CHILDREN
        )

    def is_story_scoped(self) -> bool:
        """Check if role's primary scope is story-level (e.g., Developer)."""
        return (
            self.story_rule.scope == VisibilityScope.ASSIGNED
            and self.task_rule.scope == VisibilityScope.ASSIGNED
        )

    def get_epic_filter_field(self) -> str | None:
        """Get field name to filter epics by."""
        if self.epic_rule.denies_all_access() or self.epic_rule.allows_all_access():
            return None
        return self.epic_rule.filter_by

    def get_story_filter_field(self) -> str | None:
        """Get field name to filter stories by."""
        if self.story_rule.denies_all_access() or self.story_rule.allows_all_access():
            return None
        return self.story_rule.filter_by

    def get_task_filter_field(self) -> str | None:
        """Get field name to filter tasks by."""
        if self.task_rule.denies_all_access() or self.task_rule.allows_all_access():
            return None
        return self.task_rule.filter_by

