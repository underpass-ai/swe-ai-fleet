"""Application layer for Ray jobs."""

from .generate_proposal import GenerateProposal
from .execute_agent_task import ExecuteAgentTask

__all__ = [
    "GenerateProposal",
    "ExecuteAgentTask",
]

