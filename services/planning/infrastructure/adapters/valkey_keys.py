"""Valkey (Redis) key schema for Planning Service."""

from planning.domain import StoryId, StoryState
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.identifiers.task_id import TaskId


class ValkeyKeys:
    """
    Static class: Centralized Valkey key schema.

    Infrastructure Responsibility:
    - Define all Redis key patterns in one place
    - Prevent typos and inconsistencies
    - Document the data model in Valkey

    Key Patterns:
    - planning:story:{story_id} → Hash with story details
    - planning:story:{story_id}:state → String with FSM state
    - planning:stories:all → Set of all story IDs
    - planning:stories:state:{state} → Set of story IDs by state
    - planning:project:{project_id} → Hash with project details
    - planning:projects:all → Set of all project IDs
    """

    # Namespace prefix
    NAMESPACE = "planning"

    @staticmethod
    def story_hash(story_id: StoryId) -> str:
        """
        Key for story details hash.

        Args:
            story_id: Story identifier.

        Returns:
            Redis key for story hash.
        """
        return f"{ValkeyKeys.NAMESPACE}:story:{story_id.value}"

    @staticmethod
    def story_state(story_id: StoryId) -> str:
        """
        Key for story FSM state (fast lookup).

        Args:
            story_id: Story identifier.

        Returns:
            Redis key for story state.
        """
        return f"{ValkeyKeys.NAMESPACE}:story:{story_id.value}:state"

    @staticmethod
    def all_stories() -> str:
        """
        Key for set containing all story IDs.

        Returns:
            Redis key for all stories set.
        """
        return f"{ValkeyKeys.NAMESPACE}:stories:all"

    @staticmethod
    def stories_by_state(state: StoryState) -> str:
        """
        Key for set containing story IDs by state.

        Args:
            state: Story state to filter by.

        Returns:
            Redis key for stories in given state.
        """
        return f"{ValkeyKeys.NAMESPACE}:stories:state:{state.to_string()}"

    @staticmethod
    def stories_by_epic(epic_id: EpicId) -> str:
        """
        Key for set containing story IDs by epic.

        Args:
            epic_id: Epic identifier.

        Returns:
            Redis key for stories in given epic.
        """
        return f"{ValkeyKeys.NAMESPACE}:stories:epic:{epic_id.value}"

    @staticmethod
    def project_hash(project_id: ProjectId) -> str:
        """
        Key for project details hash.

        Args:
            project_id: Project identifier.

        Returns:
            Redis key for project hash.
        """
        return f"{ValkeyKeys.NAMESPACE}:project:{project_id.value}"

    @staticmethod
    def all_projects() -> str:
        """
        Key for set containing all project IDs.

        Returns:
            Redis key for all projects set.
        """
        return f"{ValkeyKeys.NAMESPACE}:projects:all"

    @staticmethod
    def projects_by_status(status: str) -> str:
        """
        Key for set containing project IDs by status.

        Args:
            status: Project status string value (e.g., "active", "completed").

        Returns:
            Redis key for projects in given status.
        """
        return f"{ValkeyKeys.NAMESPACE}:projects:status:{status}"

    @staticmethod
    def epic_hash(epic_id: EpicId) -> str:
        """
        Key for epic details hash.

        Args:
            epic_id: Epic identifier.

        Returns:
            Redis key for epic hash.
        """
        return f"{ValkeyKeys.NAMESPACE}:epic:{epic_id.value}"

    @staticmethod
    def all_epics() -> str:
        """
        Key for set containing all epic IDs.

        Returns:
            Redis key for all epics set.
        """
        return f"{ValkeyKeys.NAMESPACE}:epics:all"

    @staticmethod
    def epics_by_project(project_id: ProjectId) -> str:
        """
        Key for set containing epic IDs by project.

        Args:
            project_id: Project identifier.

        Returns:
            Redis key for epics in given project.
        """
        return f"{ValkeyKeys.NAMESPACE}:epics:project:{project_id.value}"

    @staticmethod
    def task_hash(task_id: TaskId) -> str:
        """
        Key for task details hash.

        Args:
            task_id: Task identifier.

        Returns:
            Redis key for task hash.
        """
        return f"{ValkeyKeys.NAMESPACE}:task:{task_id.value}"

    @staticmethod
    def all_tasks() -> str:
        """
        Key for set containing all task IDs.

        Returns:
            Redis key for all tasks set.
        """
        return f"{ValkeyKeys.NAMESPACE}:tasks:all"

    @staticmethod
    def tasks_by_story(story_id: StoryId) -> str:
        """
        Key for set containing task IDs by story.

        Args:
            story_id: Story identifier.

        Returns:
            Redis key for tasks in given story.
        """
        return f"{ValkeyKeys.NAMESPACE}:tasks:story:{story_id.value}"

    @staticmethod
    def tasks_by_plan(plan_id: PlanId) -> str:
        """
        Key for set containing task IDs by plan.

        Args:
            plan_id: Plan identifier.

        Returns:
            Redis key for tasks in given plan.
        """
        return f"{ValkeyKeys.NAMESPACE}:tasks:plan:{plan_id.value}"

    @staticmethod
    def plan_hash(plan_id: PlanId) -> str:
        """
        Key for plan details hash.

        Args:
            plan_id: Plan identifier.

        Returns:
            Redis key for plan hash.
        """
        return f"{ValkeyKeys.NAMESPACE}:plan:{plan_id.value}"

    @staticmethod
    def all_plans() -> str:
        """
        Key for set containing all plan IDs.

        Returns:
            Redis key for all plans set.
        """
        return f"{ValkeyKeys.NAMESPACE}:plans:all"

    @staticmethod
    def plans_by_story(story_id: StoryId) -> str:
        """
        Key for set containing plan IDs by story.

        Args:
            story_id: Story identifier.

        Returns:
            Redis key for plans in given story.
        """
        return f"{ValkeyKeys.NAMESPACE}:plans:story:{story_id.value}"

    @staticmethod
    def ceremony_story_po_approval(
        ceremony_id: BacklogReviewCeremonyId, story_id: StoryId
    ) -> str:
        """
        Key for PO approval details (po_notes, po_concerns, etc.) for a story in a ceremony.

        This stores semantic context of PO approval decisions in Valkey (permanent storage),
        separate from Neo4j graph structure.

        Args:
            ceremony_id: Ceremony identifier.
            story_id: Story identifier.

        Returns:
            Redis key for PO approval hash (contains: po_notes, po_concerns,
            priority_adjustment, po_priority_reason, approved_by, approved_at).
        """
        return (
            f"{ValkeyKeys.NAMESPACE}:ceremony:{ceremony_id.value}:"
            f"story:{story_id.value}:po_approval"
        )
