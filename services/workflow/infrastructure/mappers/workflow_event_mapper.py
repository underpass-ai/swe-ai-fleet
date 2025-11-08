"""Mapper for WorkflowState to NATS event payloads.

Converts domain entities to event payloads for NATS.
Following Hexagonal Architecture (Infrastructure responsibility).
"""

from datetime import datetime

from core.shared.domain import ActionEnum

from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import NO_ROLE


class WorkflowEventMapper:
    """Maps WorkflowState to NATS event payloads.

    This is infrastructure responsibility:
    - Domain entities do NOT know about JSON/NATS
    - Mappers live in infrastructure layer
    - Each event type has its own mapping method

    Following DDD:
    - No to_dict() in domain entities
    - Explicit mappers in infrastructure
    """

    @staticmethod
    def to_state_changed_payload(
        workflow_state: WorkflowState,
        event_type: str,
    ) -> dict[str, str | int]:
        """Map WorkflowState to workflow.state.changed event payload.

        Args:
            workflow_state: Domain entity
            event_type: Event type identifier

        Returns:
            Dict ready for JSON serialization
        """
        last_transition = workflow_state.get_last_transition()

        return {
            "event_type": event_type,
            "task_id": str(workflow_state.task_id),
            "story_id": str(workflow_state.story_id),
            "from_state": (
                last_transition.from_state if last_transition else "initial"
            ),
            "to_state": workflow_state.get_current_state_value(),
            "action": (
                last_transition.get_action_value()
                if last_transition
                else ActionEnum.NO_ACTION.value
            ),
            "actor_role": (
                last_transition.get_actor_role_value() if last_transition else NO_ROLE
            ),
            "role_in_charge": workflow_state.get_role_in_charge_value(),
            "required_action": workflow_state.get_required_action_value(),
            "feedback": workflow_state.feedback or "",
            "retry_count": workflow_state.retry_count,
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def to_task_assigned_payload(
        task_id: str,
        story_id: str,
        role: str,
        action_required: str,
    ) -> dict[str, str]:
        """Map to workflow.task.assigned event payload.

        Args:
            task_id: Task identifier
            story_id: Story identifier
            role: Role that should act
            action_required: Action required

        Returns:
            Dict ready for JSON serialization
        """
        return {
            "task_id": task_id,
            "story_id": story_id,
            "role": role,
            "action_required": action_required,
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def to_validation_required_payload(
        task_id: str,
        story_id: str,
        validator_role: str,
        artifact_type: str,
    ) -> dict[str, str]:
        """Map to workflow.validation.required event payload.

        Args:
            task_id: Task identifier
            story_id: Story identifier
            validator_role: Role that should validate
            artifact_type: What to validate

        Returns:
            Dict ready for JSON serialization
        """
        return {
            "task_id": task_id,
            "story_id": story_id,
            "validator_role": validator_role,
            "artifact_type": artifact_type,
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def to_task_completed_payload(
        task_id: str,
        story_id: str,
        final_state: str,
    ) -> dict[str, str]:
        """Map to workflow.task.completed event payload.

        Args:
            task_id: Task identifier
            story_id: Story identifier
            final_state: Terminal state

        Returns:
            Dict ready for JSON serialization
        """
        return {
            "task_id": task_id,
            "story_id": story_id,
            "final_state": final_state,
            "timestamp": datetime.now().isoformat(),
        }

