"""Deliberation status enumeration."""

from enum import Enum


class DeliberationStatus(str, Enum):
    """Status of a deliberation execution.

    Represents the lifecycle states of a deliberation task:
    - SUBMITTED: Task has been submitted to Ray cluster
    - RUNNING: Task is currently executing on a Ray worker
    - COMPLETED: Task completed successfully
    - FAILED: Task failed with an error
    - NOT_FOUND: Deliberation ID not found in registry
    """

    SUBMITTED = "submitted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NOT_FOUND = "not_found"

