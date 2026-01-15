"""StepHandlerType: Enumeration of step handler types."""

from enum import Enum


class StepHandlerType(str, Enum):
    """
    Enumeration of step handler types.

    Handler types define what kind of operation a step performs:
    - deliberation_step: Multi-agent deliberation (council)
    - task_extraction_step: Extract tasks from artifacts
    - aggregation_step: Aggregate results/decisions
    - human_gate_step: Human approval gate (PO, etc.)
    - publish_step: Publish events/outputs
    """

    DELIBERATION_STEP = "deliberation_step"
    TASK_EXTRACTION_STEP = "task_extraction_step"
    AGGREGATION_STEP = "aggregation_step"
    HUMAN_GATE_STEP = "human_gate_step"
    PUBLISH_STEP = "publish_step"
