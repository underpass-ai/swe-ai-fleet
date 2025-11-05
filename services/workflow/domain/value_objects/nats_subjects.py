"""NATS subject enumeration.

Defines all NATS subjects used by the workflow service.
Following Domain-Driven Design principles.
"""

from enum import Enum


class NatsSubjects(str, Enum):
    """NATS subject identifiers.

    Domain knowledge: What NATS subjects does workflow service use?

    Consumed subjects (inputs):
    - AGENT_WORK_COMPLETED: VLLMAgent publishes when work is done

    Published subjects (outputs):
    - WORKFLOW_STATE_CHANGED: State transition occurred
    - WORKFLOW_TASK_ASSIGNED: Task ready for role
    - WORKFLOW_VALIDATION_REQUIRED: Validator should review
    - WORKFLOW_TASK_COMPLETED: Task reached terminal state
    """

    # Input subjects (consumed)
    AGENT_WORK_COMPLETED = "agent.work.completed"

    # Output subjects (published)
    WORKFLOW_STATE_CHANGED = "workflow.state.changed"
    WORKFLOW_TASK_ASSIGNED = "workflow.task.assigned"
    WORKFLOW_VALIDATION_REQUIRED = "workflow.validation.required"
    WORKFLOW_TASK_COMPLETED = "workflow.task.completed"

    def __str__(self) -> str:
        """String representation (returns the subject name)."""
        return self.value

