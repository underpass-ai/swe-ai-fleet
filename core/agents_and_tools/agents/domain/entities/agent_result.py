"""Domain entity for agent execution result."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentResult:
    """Result of agent task execution."""

    success: bool
    operations: list[dict]  # List of tool operations executed
    artifacts: dict[str, Any] = field(default_factory=dict)  # commit_sha, files_changed, etc
    audit_trail: list[dict] = field(default_factory=list)  # Full audit log
    reasoning_log: list[dict] = field(default_factory=list)  # Agent's internal thoughts
    error: str | None = None  # Error message if failed

