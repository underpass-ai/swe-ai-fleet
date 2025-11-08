"""ContextSectionType enum - Types of context sections for agents."""

from enum import Enum


class ContextSectionType(str, Enum):
    """Types of context sections that can be assembled for agent prompts.

    Each type represents a specific category of information that agents need
    to understand their work context.
    """

    # Identity sections
    STORY_IDENTIFICATION = "story_identification"
    EPIC_CONTEXT = "epic_context"

    # Planning sections
    PLAN_RATIONALE = "plan_rationale"
    PLAN_STATUS = "plan_status"
    ROLE_TASKS = "role_tasks"

    # Decision sections
    DECISION_CONTEXT = "decision_context"
    DECISION_DEPENDENCIES = "decision_dependencies"
    DECISION_IMPACTS = "decision_impacts"

    # Work context sections
    CURRENT_WORK = "current_work"
    TASK_DEPENDENCIES = "task_dependencies"

    # Historical sections
    MILESTONES = "milestones"
    SUMMARY_LAST = "summary_last"
    HISTORICAL_CONTEXT = "historical_context"

    # Constraints sections
    CONSTRAINTS = "constraints"
    ACCEPTANCE_CRITERIA = "acceptance_criteria"

    # Meta sections
    TOKEN_BUDGET = "token_budget"
    SCOPE_INFO = "scope_info"

    def is_identity_section(self) -> bool:
        """Check if this is an identity/context section.

        Returns:
            True if section identifies the story/epic
        """
        return self in {
            ContextSectionType.STORY_IDENTIFICATION,
            ContextSectionType.EPIC_CONTEXT,
        }

    def is_decision_section(self) -> bool:
        """Check if this is a decision-related section.

        Returns:
            True if section contains decision information
        """
        return self in {
            ContextSectionType.DECISION_CONTEXT,
            ContextSectionType.DECISION_DEPENDENCIES,
            ContextSectionType.DECISION_IMPACTS,
        }

    def is_work_section(self) -> bool:
        """Check if this is a work/task section.

        Returns:
            True if section contains current work information
        """
        return self in {
            ContextSectionType.CURRENT_WORK,
            ContextSectionType.ROLE_TASKS,
            ContextSectionType.TASK_DEPENDENCIES,
        }

    def get_default_priority(self) -> int:
        """Get default priority for this section type.

        Returns:
            Priority value (higher = appears first)
        """
        priorities = {
            # Identity first (highest priority)
            ContextSectionType.STORY_IDENTIFICATION: 100,
            ContextSectionType.EPIC_CONTEXT: 95,

            # Planning context
            ContextSectionType.PLAN_RATIONALE: 90,
            ContextSectionType.PLAN_STATUS: 85,

            # Current work (high priority)
            ContextSectionType.CURRENT_WORK: 80,
            ContextSectionType.ROLE_TASKS: 75,

            # Decision context
            ContextSectionType.DECISION_CONTEXT: 70,
            ContextSectionType.DECISION_DEPENDENCIES: 65,
            ContextSectionType.DECISION_IMPACTS: 60,

            # Constraints
            ContextSectionType.CONSTRAINTS: 55,
            ContextSectionType.ACCEPTANCE_CRITERIA: 50,

            # Historical (lower priority)
            ContextSectionType.MILESTONES: 40,
            ContextSectionType.SUMMARY_LAST: 35,
            ContextSectionType.HISTORICAL_CONTEXT: 30,

            # Meta (lowest priority)
            ContextSectionType.TOKEN_BUDGET: 10,
            ContextSectionType.SCOPE_INFO: 5,
        }
        return priorities.get(self, 50)  # Default to middle priority

