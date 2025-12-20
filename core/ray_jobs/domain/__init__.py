"""Domain models for Ray jobs."""

from .agent_config import AgentConfig
from .agent_result import AgentResult
from .agent_role import ROLE_CONTEXTS, AgentRole, get_role_context
from .agent_task import AgentTask
from .execution_request import ExecutionRequest
from .ports import IAsyncExecutor, ILLMClient, IResultPublisher, IVLLMClient
from .system_prompt import SystemPrompt
from .task_prompt import TaskPrompt
from .task_extraction_schema import TASK_EXTRACTION_SCHEMA
from .vllm_request import Message, VLLMRequest
from .vllm_response import VLLMResponse

__all__ = [
    "AgentRole",
    "ROLE_CONTEXTS",
    "get_role_context",
    "AgentConfig",
    "AgentTask",
    "ExecutionRequest",
    "SystemPrompt",
    "TaskPrompt",
    "TASK_EXTRACTION_SCHEMA",
    "VLLMRequest",
    "Message",
    "VLLMResponse",
    "AgentResult",
    "IResultPublisher",
    "ILLMClient",
    "IVLLMClient",
    "IAsyncExecutor",
]

