"""Application layer for Ray jobs."""

from .execute_agent_task import ExecuteAgentTask
from .generate_proposal import GenerateProposal

__all__ = [
    "GenerateProposal",
    "ExecuteAgentTask",
]

