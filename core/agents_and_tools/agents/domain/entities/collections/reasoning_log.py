"""Domain entity for reasoning log entry."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ReasoningLogEntry:
    """Single reasoning log entry."""

    agent_id: str  # Agent identifier
    role: str  # Agent role
    iteration: int  # Iteration number
    thought_type: str  # Type of thought (analysis, decision, action, observation, conclusion, error)
    content: str  # Thought content
    related_operations: list[str]  # Related tool operations
    confidence: float | None  # Confidence level (0.0-1.0)
    timestamp: datetime  # When the thought occurred

