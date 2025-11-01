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

Hexagonal Architecture:
- Domain: LLMClientPort (interface)
- Infrastructure: VLLMClientAdapter (implementation)
- Application: GeneratePlanUseCase, GenerateNextActionUseCase
"""

from core.agents_and_tools.agents.domain.entities import AgentResult, AgentThought
from core.agents_and_tools.agents.vllm_agent import VLLMAgent

try:
    from core.agents_and_tools.agents.application.usecases.generate_next_action_usecase import (
        GenerateNextActionUseCase,
    )
    from core.agents_and_tools.agents.application.usecases.generate_plan_usecase import GeneratePlanUseCase
    from core.agents_and_tools.agents.domain.ports.llm_client import LLMClientPort
    from core.agents_and_tools.agents.domain.ports.profile_loader_port import ProfileLoaderPort
    from core.agents_and_tools.agents.infrastructure.adapters.vllm_client_adapter import VLLMClientAdapter
    from core.agents_and_tools.agents.infrastructure.adapters.yaml_profile_adapter import (
        YamlProfileLoaderAdapter,
    )

    __all__ = [
        "AgentResult",
        "AgentThought",
        "VLLMAgent",
        "ProfileLoaderPort",
        "YamlProfileLoaderAdapter",
        "LLMClientPort",
        "VLLMClientAdapter",
        "GeneratePlanUseCase",
        "GenerateNextActionUseCase",
    ]
except ImportError:
    # May be missing dependencies
    __all__ = ["AgentResult", "AgentThought", "VLLMAgent"]

