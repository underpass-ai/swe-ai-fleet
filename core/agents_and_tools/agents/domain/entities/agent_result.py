"""Domain entity for agent execution result."""

from dataclasses import dataclass, field

from core.agents_and_tools.agents.domain.entities.artifacts import Artifacts
from core.agents_and_tools.agents.domain.entities.audit_trails import AuditTrails
from core.agents_and_tools.agents.domain.entities.operations import Operations
from core.agents_and_tools.agents.domain.entities.reasoning_logs import ReasoningLogs


@dataclass(frozen=True)
class AgentResult:
    """Result of agent task execution."""

    success: bool
    operations: Operations  # Collection of tool operations executed
    artifacts: Artifacts = field(default_factory=Artifacts)  # commit_sha, files_changed, etc
    audit_trail: AuditTrails = field(default_factory=AuditTrails)  # Full audit log
    reasoning_log: ReasoningLogs = field(default_factory=ReasoningLogs)  # Agent's internal thoughts
    error: str | None = None  # Error message if failed

