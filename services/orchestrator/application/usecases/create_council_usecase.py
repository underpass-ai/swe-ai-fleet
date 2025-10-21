"""Use case for creating a council with agents."""

from __future__ import annotations

from typing import Any, NamedTuple

from services.orchestrator.domain.entities import AgentCollection, AgentType, CouncilRegistry


class CouncilCreationResult(NamedTuple):
    """Result of council creation.
    
    Attributes:
        council_id: Unique identifier for the created council
        agents_created: Number of agents created
        agent_ids: List of created agent IDs
        council: The created council instance
    """
    council_id: str
    agents_created: int
    agent_ids: list[str]
    council: Any


class CreateCouncilUseCase:
    """Use case for creating a council with vLLM agents.
    
    Encapsulates the business logic for council creation, including:
    - Agent collection creation
    - Council instantiation
    - Registry updates
    
    Follows Single Responsibility Principle: only handles council creation.
    """
    
    def __init__(self, council_registry: CouncilRegistry):
        """Initialize the use case.
        
        Args:
            council_registry: Registry to store the created council
        """
        self._council_registry = council_registry
    
    def execute(
        self,
        role: str,
        num_agents: int,
        vllm_config: Any,
        agent_factory: Any,
        council_factory: Any,
        scoring_tool: Any,
        agent_type_str: str = "RAY_VLLM",
        custom_params: dict | None = None
    ) -> CouncilCreationResult:
        """Create a council for the given role.
        
        Args:
            role: Role name for the council (e.g., "Coder", "Architect")
            num_agents: Number of agents to create (default: 3)
            vllm_config: VLLMConfig instance for agent configuration
            agent_factory: Factory function to create agents
            council_factory: Factory function to create council (Deliberate)
            scoring_tool: Scoring tool for the council
            agent_type_str: Agent type string (default: "RAY_VLLM")
            custom_params: Optional custom parameters for agents
            
        Returns:
            CouncilCreationResult with council details
            
        Raises:
            ValueError: If council already exists or invalid agent type
            RuntimeError: If council creation fails
            
        Example:
            >>> registry = CouncilRegistry()
            >>> use_case = CreateCouncilUseCase(registry)
            >>> result = use_case.execute(
            ...     "Coder", 3, vllm_config, agent_factory, council_factory, scoring
            ... )
        """
        # Fail-fast: Role must be provided
        if not role or not role.strip():
            raise ValueError("Role cannot be empty")
        
        # Fail-fast: num_agents must be positive
        if num_agents <= 0:
            raise ValueError(f"num_agents must be positive, got {num_agents}")
        
        # Fail-fast: Council must not already exist
        if self._council_registry.has_council(role):
            raise ValueError(
                f"Council for role {role} already exists. "
                f"Delete existing council first or use a different role name."
            )
        
        # Validate agent type (raises ValueError if MOCK)
        AgentType.from_string(agent_type_str)
        
        # Create agent collection
        agent_collection = AgentCollection()
        
        # Tell, Don't Ask: AgentCollection handles agent creation
        agent_collection.create_and_add_agents(
            role=role,
            num_agents=num_agents,
            vllm_config=vllm_config,
            agent_factory=agent_factory,
            custom_params=custom_params
        )
        
        # Fail-fast: Ensure agents were created
        if agent_collection.is_empty:
            raise RuntimeError(
                f"Failed to create agents for role {role}. "
                f"AgentCollection is empty after creation."
            )
        
        # Create council using factory
        council = council_factory(
            agents=agent_collection.get_all_agents(),
            tooling=scoring_tool,
            rounds=1,
        )
        
        # Register council in registry (Tell, Don't Ask)
        self._council_registry.register_council(
            role=role,
            council=council,
            agents=agent_collection.get_all_agents()
        )
        
        # Generate council ID
        council_id = f"council-{role.lower()}"
        
        # Return complete result
        return CouncilCreationResult(
            council_id=council_id,
            agents_created=agent_collection.count,
            agent_ids=agent_collection.get_all_ids(),
            council=council
        )

