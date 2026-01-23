"""ContextKey: Enum of execution context keys."""

from enum import Enum


class ContextKey(str, Enum):
    """Execution context keys used across the ceremony engine."""

    HUMAN_APPROVALS = "human_approvals"
    IDEMPOTENCY_KEY = "idempotency_key"
    INPUTS = "inputs"
    PUBLISH_DATA = "publish_data"
    STEP_OUTPUTS = "step_outputs"
    DEFINITION = "definition"
