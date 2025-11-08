"""MilestoneEventType enum - Types of milestone events in planning."""

from enum import Enum


class MilestoneEventType(str, Enum):
    """Types of planning events that are considered milestones.

    Milestones are significant events in the story lifecycle that
    mark important progress points.
    """

    # Story creation
    CREATE_CASE_SPEC = "create_case_spec"
    CREATE_STORY_SPEC = "create_story_spec"  # Alias

    # Planning
    PROPOSE_PLAN = "propose_plan"
    PLAN_DRAFTED = "plan_drafted"  # Alias

    # Human interaction
    HUMAN_EDIT = "human_edit"
    HUMAN_FEEDBACK = "human_feedback"  # Alias

    # Approval
    APPROVE_PLAN = "approve_plan"
    PLAN_APPROVED = "plan_approved"  # Alias

    # Story lifecycle
    STORY_ACCEPTED = "story_accepted"
    STORY_REJECTED = "story_rejected"
    STORY_COMPLETED = "story_completed"

    def __str__(self) -> str:
        """Return the string value."""
        return self.value

    @classmethod
    def get_default_milestone_events(cls) -> set["MilestoneEventType"]:
        """Get the default set of events considered as milestones.

        Returns:
            Set of milestone event types
        """
        return {
            cls.CREATE_CASE_SPEC,
            cls.PROPOSE_PLAN,
            cls.HUMAN_EDIT,
            cls.APPROVE_PLAN,
        }

    @classmethod
    def get_all_milestone_events(cls) -> set["MilestoneEventType"]:
        """Get all milestone event types.

        Returns:
            Set of all milestone event types
        """
        return set(cls)

