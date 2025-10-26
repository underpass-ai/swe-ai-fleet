"""
Bounded Context: Agents and Tools

This bounded context contains:
- Agents (VLLMAgent, AgentResult, etc.) in `agents/`
- Tools (FileTool, GitTool, etc.) in `tools/`

Note: This is a legacy bounded context where agents are still coupled to tools.
Future refactoring would decouple tools via ports/adapters pattern.
"""

from core.agents_and_tools.agents import AgentResult, AgentThought, VLLMAgent, get_profile_for_role

__all__ = [
    "AgentResult",
    "AgentThought",
    "VLLMAgent",
    "get_profile_for_role",
]

