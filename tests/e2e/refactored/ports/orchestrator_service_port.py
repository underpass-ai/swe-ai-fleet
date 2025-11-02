"""Port for Orchestrator Service gRPC integration."""

from typing import Protocol


class OrchestratorServicePort(Protocol):
    """Interface for Orchestrator Service gRPC operations."""

    async def create_council(
        self,
        role: str,
        num_agents: int,
        agent_type: str,
        model_profile: str
    ) -> tuple[str, int, list[str]]:
        """Create a council for a specific role.
        
        Args:
            role: Council role (DEV, QA, ARCHITECT, etc.)
            num_agents: Number of agents in council
            agent_type: Agent type (MOCK, VLLM, RAY_VLLM)
            model_profile: Model profile for agents
            
        Returns:
            Tuple of (council_id, agents_created, agent_ids)
            
        Raises:
            RuntimeError: If service call fails
        """
        ...

    async def deliberate(
        self,
        task_description: str,
        role: str,
        rounds: int,
        num_agents: int,
        constraints: dict[str, str]
    ) -> tuple[list[dict], str, int]:
        """Execute peer deliberation on a task.
        
        Args:
            task_description: Task to deliberate
            role: Council role to use
            rounds: Number of peer review rounds
            num_agents: Number of agents in council
            constraints: Task constraints (rubric, requirements, etc.)
            
        Returns:
            Tuple of (results, winner_id, duration_ms)
            
        Raises:
            RuntimeError: If service call fails
        """
        ...

    async def delete_council(self, role: str) -> tuple[bool, int]:
        """Delete a council and its agents.
        
        Args:
            role: Role of the council to delete
            
        Returns:
            Tuple of (success, agents_removed)
            
        Raises:
            RuntimeError: If service call fails
        """
        ...

