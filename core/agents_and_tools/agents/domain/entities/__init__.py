"""Domain entities for agents.

Entities are organized into logical subdirectories:
- core/: Core agent entities (profile, result, execution planning)
- collections/: Collection entities (artifacts, operations, logs)
- results/: Tool execution result entities
"""

from .collections import (
    Artifact,
    Artifacts,
    AuditTrailEntry,
    AuditTrails,
    Observation,
    ObservationHistories,
    Operations,
    ReasoningLogEntry,
    ReasoningLogs,
)
from .core import (
    AgentProfile,
    AgentResult,
    AgentThought,
    ExecutionConstraints,
    ExecutionPlan,
    ExecutionStep,
    Operation,
    ToolType,
)
from .results import (
    DbExecutionResult,
    DockerExecutionResult,
    FileExecutionResult,
    GitExecutionResult,
    HttpExecutionResult,
    StepExecutionResult,
    TestExecutionResult,
)

__all__ = [
    # Core entities
    "AgentProfile",
    "AgentResult",
    "AgentThought",
    "ExecutionConstraints",
    "ExecutionPlan",
    "ExecutionStep",
    "Operation",
    "ToolType",
    # Collections
    "Artifact",
    "Artifacts",
    "AuditTrailEntry",
    "AuditTrails",
    "Observation",
    "ObservationHistories",
    "Operations",
    "ReasoningLogEntry",
    "ReasoningLogs",
    # Results
    "DbExecutionResult",
    "DockerExecutionResult",
    "FileExecutionResult",
    "GitExecutionResult",
    "HttpExecutionResult",
    "StepExecutionResult",
    "TestExecutionResult",
]

