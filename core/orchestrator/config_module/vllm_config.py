"""vLLM configuration for agent deployment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.orchestrator.domain.entities import AgentConfig


@dataclass
class VLLMConfig:
    """Configuration for vLLM server connection."""
    
    # Server configuration
    vllm_url: str = "http://vllm-server-service:8000"
    model: str = "meta-llama/Llama-2-7b-chat-hf"
    
    # Generation parameters
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30
    
    # Agent configuration
    default_agent_type: str = "mock"  # "mock" or "vllm"
    
    @classmethod
    def from_env(cls) -> VLLMConfig:
        """Create VLLMConfig from environment variables.
        
        Environment variables:
            VLLM_URL: vLLM server URL (default: http://vllm-server-service:8000)
            VLLM_MODEL: Model name (default: meta-llama/Llama-2-7b-chat-hf)
            VLLM_TEMPERATURE: Temperature (default: 0.7)
            VLLM_MAX_TOKENS: Max tokens (default: 2048)
            VLLM_TIMEOUT: Timeout in seconds (default: 30)
            AGENT_TYPE: Default agent type (default: mock)
        """
        return cls(
            vllm_url=os.getenv("VLLM_URL", "http://vllm-server-service:8000"),
            model=os.getenv("VLLM_MODEL", "meta-llama/Llama-2-7b-chat-hf"),
            temperature=float(os.getenv("VLLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("VLLM_MAX_TOKENS", "2048")),
            timeout=int(os.getenv("VLLM_TIMEOUT", "30")),
            default_agent_type=os.getenv("AGENT_TYPE", "mock"),
        )
    
    def to_agent_config(self, agent_id: str, role: str) -> AgentConfig:
        """Convert to agent configuration domain entity.
        
        Args:
            agent_id: Unique identifier for the agent
            role: Role of the agent
            
        Returns:
            AgentConfig domain entity
        """
        # Import at runtime to avoid circular dependency
        from services.orchestrator.domain.entities import AgentConfig
        
        # Create extra params for fields not in AgentConfig base
        extra_params = {
            "agent_type": self.default_agent_type,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
        }
        
        return AgentConfig(
            agent_id=agent_id,
            role=role,
            vllm_url=self.vllm_url,
            model=self.model,
            temperature=self.temperature,
            extra_params=extra_params,
        )
    
    def is_vllm_enabled(self) -> bool:
        """Check if vLLM is enabled (not mock mode)."""
        return self.default_agent_type.lower() == "vllm"
    
    def __str__(self) -> str:
        """String representation of configuration."""
        return (
            f"VLLMConfig(url={self.vllm_url}, model={self.model}, "
            f"type={self.default_agent_type}, temp={self.temperature})"
        )
