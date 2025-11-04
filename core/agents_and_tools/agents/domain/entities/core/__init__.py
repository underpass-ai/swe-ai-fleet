"""Core agent domain entities."""

# Agent and AgentId are NOT auto-imported to avoid circular imports
# Import them directly: from core.agents_and_tools.agents.domain.entities.core.agent import Agent

from .agent_profile import AgentProfile
from .agent_result import AgentResult
from .agent_thought import AgentThought
from .execution_constraints import ExecutionConstraints
from .execution_plan import ExecutionPlan
from .execution_step import ExecutionStep
from .operation import Operation
from .tool_type import ToolType

__all__ = [
    "AgentProfile",
    "AgentResult",
    "AgentThought",
    "ExecutionConstraints",
    "ExecutionPlan",
    "ExecutionStep",
    "Operation",
    "ToolType",
]

