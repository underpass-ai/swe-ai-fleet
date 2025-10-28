"""Domain entity for agent execution plan."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionPlan:
    """Structured execution plan from LLM."""

    steps: list[dict]  # [{"tool": "files", "operation": "read_file", "params": {...}}]
    reasoning: str | None = None  # Why this plan

