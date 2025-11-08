"""Mapper for RoleContextFields - Infrastructure layer."""

from typing import Any

from core.context.domain.role_context_fields import RoleContextFields
from core.context.domain.role import Role
from core.context.infrastructure.mappers.story_header_mapper import StoryHeaderMapper
from core.context.infrastructure.mappers.task_plan_mapper import TaskPlanMapper
from core.context.domain.value_objects.decision_relation import DecisionRelation
from core.context.domain.value_objects.impacted_task import ImpactedTask


class RoleContextFieldsMapper:
    """Mapper for RoleContextFields serialization."""

    @staticmethod
    def to_dict(fields: RoleContextFields) -> dict[str, Any]:
        """Convert RoleContextFields to dictionary for serialization.

        Args:
            fields: RoleContextFields domain value object

        Returns:
            Dictionary representation
        """
        return {
            "role": fields.role.value,
            "story_header": StoryHeaderMapper.to_dict(fields.story_header),
            "plan_header": fields.plan_header.to_dict(),
            "role_tasks": [TaskPlanMapper.to_dict(task) for task in fields.role_tasks],
            "decisions_relevant": [d.to_dict() for d in fields.decisions_relevant],
            "decision_dependencies": [
                {
                    "src_id": rel.source_decision_id.to_string(),
                    "dst_id": rel.target_decision_id.to_string(),
                    "rel_type": rel.relation_type.value,  # Serialize enum
                }
                for rel in fields.decision_dependencies
            ],
            "impacted_tasks": [
                {
                    "decision_id": impact.decision_id.to_string(),
                    "task_id": impact.task_id.to_string(),
                    "title": impact.title,
                }
                for impact in fields.impacted_tasks
            ],
            "recent_milestones": [
                {
                    "event_type": m.event_type.value,
                    "ts_ms": m.timestamp_ms,
                    "event_id": m.event_id,
                    "metadata": m.metadata,
                }
                for m in fields.recent_milestones
            ],
            "last_summary": fields.last_summary,
            "token_budget_hint": fields.token_budget_hint,
        }

