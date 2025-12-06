"""Domain value object for task decision metadata.

Represents decision context from Planning Service's FASE 1+2 (Backlog Review Ceremony).
This metadata explains WHY a task was selected and provides council feedback.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskDecisionMetadata:
    """Immutable value object representing task decision context.

    This captures the decision made by technical councils (ARCHITECT, QA, DEVOPS)
    during backlog review or planning meetings about why a specific task is necessary.

    Domain Invariants:
    - decided_by cannot be empty
    - decision_reason cannot be empty
    - council_feedback cannot be empty
    - source must be valid (BACKLOG_REVIEW or PLANNING_MEETING)
    """

    decided_by: str  # Council that made decision (ARCHITECT, QA, DEVOPS)
    decision_reason: str  # WHY this task exists
    council_feedback: str  # Full council analysis and reasoning
    decided_at: str  # ISO timestamp of decision
    source: str  # Origin (BACKLOG_REVIEW, PLANNING_MEETING)

    def __post_init__(self) -> None:
        """Validate domain invariants (fail-fast)."""
        if not self.decided_by or not self.decided_by.strip():
            raise ValueError("decided_by cannot be empty")

        if not self.decision_reason or not self.decision_reason.strip():
            raise ValueError("decision_reason cannot be empty")

        if not self.council_feedback or not self.council_feedback.strip():
            raise ValueError("council_feedback cannot be empty")

        if not self.decided_at or not self.decided_at.strip():
            raise ValueError("decided_at cannot be empty")

        valid_sources = {"BACKLOG_REVIEW", "PLANNING_MEETING", "UNKNOWN"}
        if self.source not in valid_sources:
            raise ValueError(f"Invalid source: {self.source}. Must be one of {valid_sources}")

    def format_for_llm(self) -> str:
        """Format decision metadata as human-readable context for LLM agents.

        Returns:
            Formatted string with decision context structured for agent consumption
        """
        return f"""
╔══════════════════════════════════════════════════════════════╗
║              TASK DECISION CONTEXT (WHY THIS TASK)          ║
╚══════════════════════════════════════════════════════════════╝

DECIDED BY: {self.decided_by} Council

DECISION REASON:
{self.decision_reason}

FULL COUNCIL ANALYSIS:
{self.council_feedback}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SOURCE: {self.source}
DECIDED AT: {self.decided_at}

⚠️  This task was identified by the {self.decided_by} council
   during {self.source.lower().replace('_', ' ')} as technically necessary.

   Use this decision context to inform your implementation choices and
   ensure alignment with the original technical reasoning.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""



