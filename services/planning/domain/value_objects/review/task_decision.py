"""TaskDecision - Value Object for high-level task decision metadata.

Value Object (Domain Layer):
- Immutable record of WHY a task was identified
- Contains decision context from councils
- Used in PlanPreliminary to explain tasks_outline

Following DDD:
- Immutable (@dataclass(frozen=True))
- Fail-fast validation
- Rich domain model with decision semantics
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TaskDecision:
    """
    Decision metadata for a high-level task identified during Backlog Review.

    Explains:
    - WHAT: task_description
    - WHO: decided_by (ARCHITECT, QA, DEVOPS)
    - WHY: decision_reason
    - CONTEXT: council_feedback (full feedback from council)
    - WHEN: decided_at

    Domain Invariants:
    - task_description cannot be empty
    - decided_by must be valid role
    - decision_reason cannot be empty
    - council_feedback cannot be empty
    - task_index must be >= 0

    Usage:
        task_decision = TaskDecision(
            task_description="Setup JWT middleware",
            decided_by="ARCHITECT",
            decision_reason="JWT standard for stateless authentication...",
            council_feedback="ARCHITECT analysis: User auth requires...",
            task_index=0,
            decided_at=datetime.now(UTC),
        )
    """

    task_description: str  # "Setup JWT middleware"
    decided_by: str  # "ARCHITECT", "QA", "DEVOPS"
    decision_reason: str  # Why this task is needed
    council_feedback: str  # Full feedback from council
    task_index: int  # Order in tasks_outline
    decided_at: datetime  # When decision was made

    def __post_init__(self) -> None:
        """
        Validate TaskDecision (fail-fast).

        Raises:
            ValueError: If any validation fails
        """
        if not self.task_description or not self.task_description.strip():
            raise ValueError("task_description cannot be empty")

        valid_roles = ("ARCHITECT", "QA", "DEVOPS", "DEV", "DATA", "PO")
        if self.decided_by not in valid_roles:
            raise ValueError(
                f"Invalid decided_by: {self.decided_by}. "
                f"Must be one of {valid_roles}"
            )

        if not self.decision_reason or not self.decision_reason.strip():
            raise ValueError("decision_reason cannot be empty")

        if not self.council_feedback or not self.council_feedback.strip():
            raise ValueError("council_feedback cannot be empty")

        if self.task_index < 0:
            raise ValueError(f"task_index must be >= 0, got {self.task_index}")






