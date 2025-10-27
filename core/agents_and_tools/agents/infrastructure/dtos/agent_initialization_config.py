"""Domain entity for agent initialization configuration."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class AgentInitializationConfig:
    """Configuration for initializing VLLMAgent.

    This entity encapsulates all the parameters needed to initialize
    a VLLMAgent, keeping the initialization logic within the domain.

    Attributes:
        agent_id: Unique agent identifier
        role: Agent role (DEV, QA, ARCHITECT, etc.) - must be uppercase
        workspace_path: Path to workspace directory
        vllm_url: Optional vLLM server URL
        audit_callback: Optional callback for audit logging
        enable_tools: Whether to enable tool execution
    """

    agent_id: str
    role: str
    workspace_path: Path
    vllm_url: str | None = None
    audit_callback: Callable | None = None
    enable_tools: bool = True

    def __post_init__(self):
        """Validate configuration (fail-fast).

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.agent_id:
            raise ValueError("Agent ID cannot be empty")

        if not self.role:
            raise ValueError("Agent role cannot be empty")

        # Role must be uppercase (caller responsibility)
        if self.role != self.role.upper():
            raise ValueError(f"Agent role must be uppercase, got: {self.role}")

        if not self.workspace_path.exists():
            raise ValueError(f"Workspace path does not exist: {self.workspace_path}")

