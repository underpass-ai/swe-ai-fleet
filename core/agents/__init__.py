"""
Intelligent agents for SWE AI Fleet.

VLLMAgent is the universal agent class used by all roles in the system.
Each role (DEV, QA, ARCHITECT, DEVOPS, DATA) uses the same VLLMAgent class
but with different tool usage patterns and role-specific models.

Role-Specific Models:
- ARCHITECT: databricks/dbrx-instruct (128K context, temp 0.3)
- DEV: deepseek-coder:33b (32K context, temp 0.7)
- QA: mistralai/Mistral-7B-Instruct-v0.3 (32K context, temp 0.5)
- DEVOPS: Qwen/Qwen2.5-Coder-14B-Instruct (32K context, temp 0.6)
- DATA: deepseek-ai/deepseek-coder-6.7b-instruct (32K context, temp 0.7)

VLLMClient provides the interface to vLLM for intelligent planning.
"""

from core.agents.profile_loader import get_profile_for_role
from core.agents.vllm_agent import AgentResult, AgentThought, VLLMAgent

try:
    from core.agents.vllm_client import VLLMClient
    __all__ = ["AgentResult", "AgentThought", "VLLMAgent", "VLLMClient", "get_profile_for_role"]
except ImportError:
    # vllm_client requires aiohttp
    __all__ = ["AgentResult", "AgentThought", "VLLMAgent", "get_profile_for_role"]

