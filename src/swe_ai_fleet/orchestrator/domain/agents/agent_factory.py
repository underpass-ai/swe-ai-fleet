"""Agent factory for creating different types of agents.

This module provides a factory pattern to create agents based on configuration,
supporting both MockAgent for testing and VLLMAgent for production.
"""

from __future__ import annotations

import logging
from typing import Any

from .agent import Agent
from .mock_agent import AgentBehavior, MockAgent
from .model_adapter import ModelAgentAdapter
from .vllm_agent import AsyncVLLMAgent

logger = logging.getLogger(__name__)


class AgentType:
    """Enum-like class for agent types."""
    MOCK = "mock"
    VLLM = "vllm"
    MODEL = "model"  # Uses models/ bounded context


class AgentFactory:
    """Factory for creating agents based on configuration."""
    
    @staticmethod
    def create_agent(
        agent_id: str,
        role: str,
        agent_type: str = AgentType.MOCK,
        **kwargs: Any,
    ) -> Agent:
        """Create an agent instance based on type.
        
        Args:
            agent_id: Unique identifier for the agent
            role: Role of the agent (e.g., "DEV", "QA", "ARCHITECT")
            agent_type: Type of agent to create ("mock" or "vllm")
            **kwargs: Additional configuration parameters
            
        Returns:
            Agent instance
            
        Raises:
            ValueError: If agent_type is not supported
        """
        logger.info(f"Creating {agent_type} agent {agent_id} with role {role}")
        
        if agent_type == AgentType.MOCK:
            return AgentFactory._create_mock_agent(agent_id, role, **kwargs)
        elif agent_type == AgentType.VLLM:
            return AgentFactory._create_vllm_agent(agent_id, role, **kwargs)
        elif agent_type == AgentType.MODEL:
            return AgentFactory._create_model_agent(agent_id, role, **kwargs)
        else:
            raise ValueError(f"Unsupported agent type: {agent_type}")
    
    @staticmethod
    def _create_mock_agent(
        agent_id: str,
        role: str,
        behavior: str = "normal",
        seed: int | None = None,
        **kwargs: Any,
    ) -> MockAgent:
        """Create a MockAgent instance.
        
        Args:
            agent_id: Unique identifier for the agent
            role: Role of the agent
            behavior: Behavior type ("normal", "excellent", "poor", etc.)
            seed: Random seed for reproducible behavior
            **kwargs: Additional parameters (ignored for MockAgent)
            
        Returns:
            MockAgent instance
        """
        try:
            behavior_enum = AgentBehavior(behavior)
        except ValueError:
            logger.warning(f"Invalid behavior '{behavior}', using NORMAL")
            behavior_enum = AgentBehavior.NORMAL
        
        return MockAgent(
            agent_id=agent_id,
            role=role,
            behavior=behavior_enum,
            seed=seed,
        )
    
    @staticmethod
    def _create_vllm_agent(
        agent_id: str,
        role: str,
        vllm_url: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 30,
        **kwargs: Any,
    ) -> AsyncVLLMAgent:
        """Create a VLLMAgent instance.
        
        Args:
            agent_id: Unique identifier for the agent
            role: Role of the agent
            vllm_url: Base URL of the vLLM server
            model: Model name to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            **kwargs: Additional parameters (ignored for VLLMAgent)
            
        Returns:
            AsyncVLLMAgent instance
        """
        return AsyncVLLMAgent(
            agent_id=agent_id,
            role=role,
            vllm_url=vllm_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    
    @staticmethod
    def _create_model_agent(
        agent_id: str,
        role: str,
        profile_path: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 30,
        **kwargs: Any,
    ) -> ModelAgentAdapter:
        """Create a ModelAgentAdapter instance.
        
        Args:
            agent_id: Unique identifier for the agent
            role: Role of the agent
            profile_path: Path to model profile YAML file (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            **kwargs: Additional parameters (ignored for ModelAgentAdapter)
            
        Returns:
            ModelAgentAdapter instance
        """
        from swe_ai_fleet.models.loaders import get_model_from_env
        
        # Get model from environment
        model = get_model_from_env()
        
        if profile_path:
            # Load profile and use it to configure the adapter
            from .model_adapter import create_model_agent_from_profile
            return create_model_agent_from_profile(
                profile_path=profile_path,
                agent_id=agent_id,
                role=role,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
        else:
            # Create adapter with default configuration
            return ModelAgentAdapter(
                model=model,
                agent_id=agent_id,
                role=role,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
    
    @staticmethod
    def create_council(
        role: str,
        num_agents: int = 3,
        agent_type: str = AgentType.MOCK,
        agent_configs: list[dict[str, Any]] | None = None,
    ) -> list[Agent]:
        """Create a council of agents.
        
        Args:
            role: Role for all agents in the council
            num_agents: Number of agents to create
            agent_type: Type of agents to create
            agent_configs: Optional list of specific configs for each agent
            
        Returns:
            List of Agent instances
            
        Example:
            >>> # Create mock council
            >>> council = AgentFactory.create_council("DEV", 3, "mock")
            
            >>> # Create vLLM council with custom configs
            >>> configs = [
            ...     {"model": "llama-2-7b", "temperature": 0.7},
            ...     {"model": "llama-2-13b", "temperature": 0.5},
            ...     {"model": "llama-2-7b", "temperature": 0.9},
            ... ]
            >>> council = AgentFactory.create_council(
            ...     "DEV", 3, "vllm", 
            ...     agent_configs=configs
            ... )
        """
        agents = []
        
        for i in range(num_agents):
            agent_id = f"agent-{role.lower()}-{i:03d}"
            
            # Get config for this agent
            config = {}
            if agent_configs and i < len(agent_configs):
                config = agent_configs[i]
            
            # Add required configs
            config.update({
                "agent_id": agent_id,
                "role": role,
                "agent_type": agent_type,
            })
            
            agent = AgentFactory.create_agent(**config)
            agents.append(agent)
        
        logger.info(f"Created {num_agents} {agent_type} agents for {role} council")
        return agents


def create_agent_from_config(config: dict[str, Any]) -> Agent:
    """Create an agent from a configuration dictionary.
    
    Args:
        config: Configuration dictionary containing agent parameters
        
    Returns:
        Agent instance
        
    Example:
        >>> config = {
        ...     "agent_id": "agent-dev-001",
        ...     "role": "DEV",
        ...     "agent_type": "vllm",
        ...     "vllm_url": "http://localhost:8000",
        ...     "model": "meta-llama/Llama-2-7b-chat-hf",
        ...     "temperature": 0.7,
        ... }
        >>> agent = create_agent_from_config(config)
    """
    agent_type = config.pop("agent_type", AgentType.MOCK)
    agent_id = config.pop("agent_id")
    role = config.pop("role")
    
    return AgentFactory.create_agent(
        agent_id=agent_id,
        role=role,
        agent_type=agent_type,
        **config
    )
