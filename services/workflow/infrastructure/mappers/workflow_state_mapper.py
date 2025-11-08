"""Mapper for WorkflowState serialization.

Converts WorkflowState domain entity to/from JSON for Valkey cache.
Following Hexagonal Architecture (Infrastructure responsibility).
"""

import json
from datetime import datetime

from core.shared.domain import Action, ActionEnum

from services.workflow.domain.entities.state_transition import StateTransition
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


class WorkflowStateMapper:
    """Maps WorkflowState to/from JSON for Valkey cache.

    This is infrastructure responsibility:
    - Domain entities do NOT know about JSON/serialization
    - Mappers live in infrastructure layer
    - Explicit conversions (no reflection)

    Following DDD:
    - No to_dict() in domain entities
    - Tell, Don't Ask: Use domain methods for attribute access
    - Type-safe conversions
    """

    @staticmethod
    def to_json(state: WorkflowState) -> str:
        """Convert WorkflowState to JSON string (for Valkey).

        Tell, Don't Ask: Uses WorkflowState and StateTransition methods
        instead of direct attribute access.

        Args:
            state: Domain entity

        Returns:
            JSON string suitable for Valkey storage
        """
        data = {
            "task_id": str(state.task_id),
            "story_id": str(state.story_id),
            "current_state": state.get_current_state_value(),
            "role_in_charge": state.get_role_in_charge_value(),
            "required_action": state.get_required_action_value(),
            "feedback": state.feedback,
            "updated_at": state.updated_at.isoformat(),
            "retry_count": state.retry_count,
            "history": [
                {
                    "from_state": t.from_state,
                    "to_state": t.to_state,
                    "action": t.get_action_value(),
                    "actor_role": t.get_actor_role_value(),
                    "timestamp": t.timestamp.isoformat(),
                    "feedback": t.feedback,
                }
                for t in state.history
            ],
        }

        return json.dumps(data)

    @staticmethod
    def from_json(json_str: str | bytes) -> WorkflowState:
        """Deserialize JSON string from Valkey to WorkflowState.

        Reconstructs full domain entity with all value objects.

        Args:
            json_str: JSON string or bytes from Valkey

        Returns:
            WorkflowState domain entity

        Raises:
            json.JSONDecodeError: If JSON is invalid
            ValueError: If data is invalid (domain validation)
        """
        data = json.loads(json_str)

        # Parse transitions
        transitions = []
        for t_data in data["history"]:
            transitions.append(
                StateTransition(
                    from_state=t_data["from_state"],
                    to_state=t_data["to_state"],
                    action=Action(value=ActionEnum(t_data["action"])),
                    actor_role=Role(t_data["actor_role"]),
                    timestamp=datetime.fromisoformat(t_data["timestamp"]),
                    feedback=t_data.get("feedback"),
                )
            )

        # Parse role_in_charge (optional)
        role_in_charge = None
        if data.get("role_in_charge"):
            role_in_charge = Role(data["role_in_charge"])

        # Parse required_action (optional)
        required_action = None
        if data.get("required_action"):
            required_action = Action(value=ActionEnum(data["required_action"]))

        return WorkflowState(
            task_id=TaskId(data["task_id"]),
            story_id=StoryId(data["story_id"]),
            current_state=WorkflowStateEnum(data["current_state"]),
            role_in_charge=role_in_charge,
            required_action=required_action,
            history=tuple(transitions),
            feedback=data.get("feedback"),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            retry_count=data.get("retry_count", 0),
        )

