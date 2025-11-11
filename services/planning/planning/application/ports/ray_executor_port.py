"""Port (interface) for Ray Executor communication.

Following Hexagonal Architecture:
- Application layer defines the port (this interface)
- Infrastructure layer provides the adapter (gRPC client)

Planning Service uses Ray Executor to submit LLM jobs for task derivation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from planning.domain.value_objects.actors.role import Role
from planning.domain.value_objects.identifiers.deliberation_id import DeliberationId
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.task_derivation.llm_prompt import LLMPrompt


class RayExecutorError(Exception):
    """Raised when Ray Executor communication fails."""
    
    pass


class RayExecutorPort(ABC):
    """Port defining the interface for Ray Executor communication.
    
    This port abstracts Ray Executor gRPC calls,
    allowing Planning Service to submit LLM jobs without
    knowing Ray Executor implementation details.
    
    Following Hexagonal Architecture:
    - Application layer defines the port (this interface)
    - Infrastructure layer provides the adapter (gRPC client)
    
    Design: Event-Driven (Fire-and-Forget)
    - submit_task_derivation() returns immediately with DeliberationId
    - Actual execution happens asynchronously in Ray cluster
    - Result published to NATS by Ray Worker (agent.response.completed)
    - Consumer handles result processing
    
    DDD: Uses ONLY Value Objects (NO primitives)
    """
    
    @abstractmethod
    async def submit_task_derivation(
        self,
        plan_id: PlanId,
        prompt: LLMPrompt,
        role: Role,
    ) -> DeliberationId:
        """Submit task derivation job to Ray Executor.
        
        Fire-and-forget pattern:
        1. Submits job to Ray Executor (gRPC)
        2. Returns DeliberationId immediately
        3. Ray executes asynchronously
        4. Result published to NATS (not returned here)
        
        Args:
            plan_id: Plan identifier (for tracking)
            prompt: LLM prompt for task decomposition
            role: Role context for generation
            
        Returns:
            DeliberationId for tracking the async job
            
        Raises:
            RayExecutorError: If submission fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if Ray Executor is healthy.
        
        Returns:
            True if Ray Executor is reachable
        """
        pass

