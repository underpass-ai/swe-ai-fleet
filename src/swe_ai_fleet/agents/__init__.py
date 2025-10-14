"""
Intelligent agents for SWE AI Fleet.

VLLMAgent is the universal agent class used by all roles in the system.
Each role (DEV, QA, ARCHITECT, DEVOPS, DATA) uses the same VLLMAgent class
but with different tool usage patterns based on their responsibilities.

VLLMClient provides the interface to vLLM for intelligent planning.
"""

from swe_ai_fleet.agents.vllm_agent import AgentResult, AgentThought, VLLMAgent

try:
    from swe_ai_fleet.agents.vllm_client import VLLMClient
    __all__ = ["AgentResult", "AgentThought", "VLLMAgent", "VLLMClient"]
except ImportError:
    # vllm_client requires aiohttp
    __all__ = ["AgentResult", "AgentThought", "VLLMAgent"]

