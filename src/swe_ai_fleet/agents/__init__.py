"""
Intelligent agents for SWE AI Fleet.

VLLMAgent is the universal agent class used by all roles in the system.
Each role (DEV, QA, ARCHITECT, DEVOPS, DATA) uses the same VLLMAgent class
but with different tool usage patterns based on their responsibilities.
"""

from swe_ai_fleet.agents.vllm_agent import AgentResult, VLLMAgent

__all__ = ["AgentResult", "VLLMAgent"]

