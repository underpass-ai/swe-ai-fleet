"""Agent configuration entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from swe_ai_fleet.orchestrator.config_module.vllm_config import VLLMConfig


@dataclass
class AgentConfig:
    """Domain entity representing agent configuration.
    
    Encapsulates all configuration needed to create an agent instance.
    This is a domain entity that doesn't know about infrastructure
    details like VLLMConfig or AgentFactory.
    
    Attributes:
        agent_id: Unique identifier for the agent
        role: Agent role (e.g., "Coder", "Architect", "Reviewer")
        vllm_url: URL of the vLLM inference server
        model: Model name to use for inference
        agent_type: Type of agent to create ("vllm", "mock", "model")
        temperature: Sampling temperature for generation
        extra_params: Additional configuration parameters
    """
    
    agent_id: str
    role: str
    vllm_url: str
    model: str
    agent_type: str = "vllm"  # Default to vLLM (production), not mock
    temperature: float = 0.7
    extra_params: dict[str, Any] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary.
        
        Useful for passing to infrastructure components that expect dicts.
        
        Returns:
            Dictionary representation of the configuration
        """
        config = {
            "agent_id": self.agent_id,
            "role": self.role,
            "vllm_url": self.vllm_url,
            "model": self.model,
            "agent_type": self.agent_type,
            "temperature": self.temperature,
        }
        
        # Merge extra params if present
        if self.extra_params:
            config.update(self.extra_params)
        
        return config
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentConfig:
        """Create configuration from dictionary.
        
        Args:
            data: Dictionary containing configuration
            
        Returns:
            AgentConfig instance
        """
        # Extract known fields
        agent_id = data.pop("agent_id")
        role = data.pop("role")
        vllm_url = data.pop("vllm_url")
        model = data.pop("model")
        agent_type = data.pop("agent_type", "vllm")
        temperature = data.pop("temperature", 0.7)
        
        # Remaining fields go to extra_params
        extra_params = data if data else None
        
        return cls(
            agent_id=agent_id,
            role=role,
            vllm_url=vllm_url,
            model=model,
            agent_type=agent_type,
            temperature=temperature,
            extra_params=extra_params,
        )
    
    def with_overrides(self, **overrides) -> AgentConfig:
        """Create a new config with overridden values.
        
        Args:
            **overrides: Fields to override
            
        Returns:
            New AgentConfig instance with overrides applied
            
        Example:
            >>> config = AgentConfig(...)
            >>> new_config = config.with_overrides(temperature=0.9, model="gpt-4")
        """
        config_dict = self.to_dict()
        config_dict.update(overrides)
        return AgentConfig.from_dict(config_dict)
    
    @staticmethod
    def create(
        agent_id: str,
        role: str,
        index: int,
        vllm_config: VLLMConfig,
        custom_params: dict[str, Any] | None = None
    ) -> AgentConfig:
        """Create agent configuration from VLLMConfig with optional custom overrides.
        
        Factory method that encapsulates the creation logic for agent configurations,
        applying custom parameters if provided.
        
        Args:
            agent_id: Unique identifier for the agent
            role: Agent role (e.g., "Coder", "Architect")
            index: Agent index (used for logging/tracking)
            vllm_config: VLLMConfig instance with base configuration
            custom_params: Optional custom parameters to override defaults
            
        Returns:
            AgentConfig instance with all configurations applied
            
        Example:
            >>> from swe_ai_fleet.orchestrator.config_module.vllm_config import VLLMConfig
            >>> vllm_config = VLLMConfig.from_env()
            >>> config = AgentConfig.create(
            ...     "agent-001", "Coder", 0, vllm_config,
            ...     custom_params={"temperature": 0.9}
            ... )
        """
        # Get base config from vLLM config (returns AgentConfig)
        agent_config = vllm_config.to_agent_config(agent_id, role)
        
        # Apply custom overrides if provided
        if custom_params:
            overrides = {}
            if "vllm_url" in custom_params:
                overrides["vllm_url"] = custom_params["vllm_url"]
            if "model" in custom_params:
                overrides["model"] = custom_params["model"]
            if "temperature" in custom_params:
                overrides["temperature"] = float(custom_params["temperature"])
            
            if overrides:
                agent_config = agent_config.with_overrides(**overrides)
        
        return agent_config

