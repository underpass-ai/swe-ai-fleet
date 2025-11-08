"""EntityType Enum - Types of entities in the Context bounded context."""

from enum import Enum


class EntityType(str, Enum):
    """Types of entities that can be filtered by RBAC L3.

    Each entity type has its own set of valid columns that can be
    filtered at the column level.
    """

    STORY = "story"
    TASK = "task"
    PLAN = "plan"
    DECISION = "decision"
    EPIC = "epic"
    MILESTONE = "milestone"
    DECISION_RELATION = "decision_relation"
    IMPACTED_TASK = "impacted_task"

    @staticmethod
    def get_valid_columns(entity_type: "EntityType") -> tuple[str, ...]:
        """Get valid column names for an entity type.

        Args:
            entity_type: Entity type

        Returns:
            Tuple of valid column names for this entity type

        Note:
            This defines the complete schema for each entity type.
            Only these columns can be whitelisted in RBAC policies.
        """
        _VALID_COLUMNS: dict[EntityType, tuple[str, ...]] = {
            EntityType.STORY: (
                "story_id", "title", "description", "status",
                "assigned_to", "owner", "acceptance_criteria",
                "business_notes", "constraints", "tags",
                "estimated_hours", "budget_allocated", "created_by",
                "created_at", "updated_at",
            ),
            EntityType.TASK: (
                "task_id", "title", "description", "status", "type",
                "role", "assigned_to", "estimated_hours",
                "dependencies", "notes", "created_at", "updated_at",
            ),
            EntityType.PLAN: (
                "plan_id", "version", "story_id", "status",
                "author_id", "rationale", "created_at_ms",
            ),
            EntityType.DECISION: (
                "id", "title", "rationale", "status",
                "author_id", "created_at_ms", "kind",
            ),
            EntityType.EPIC: (
                "epic_id", "title", "description", "status",
                "assigned_to", "owner", "created_at", "updated_at",
            ),
            EntityType.MILESTONE: (
                "event_type", "ts_ms", "actor_id", "description",
            ),
            EntityType.DECISION_RELATION: (
                "src_id", "dst_id", "relation_type",
            ),
            EntityType.IMPACTED_TASK: (
                "decision_id", "task_id", "impact_description",
            ),
        }

        return _VALID_COLUMNS.get(entity_type, ())

