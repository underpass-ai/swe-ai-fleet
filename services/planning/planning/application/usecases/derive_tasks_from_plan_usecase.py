"""DeriveTasksFromPlanUseCase - Automatic task derivation using LLM.

Use Case (Application Layer):
- Orchestrates domain logic
- Depends on ports (interfaces)
- NO infrastructure dependencies
- Event-driven (fire-and-forget)
"""

import logging
from dataclasses import dataclass

from planning.application.ports import RayExecutorPort, StoragePort
from planning.domain.value_objects.actors.role import Role
from planning.domain.value_objects.identifiers.deliberation_id import DeliberationId
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.task_derivation.llm_prompt import LLMPrompt

logger = logging.getLogger(__name__)


@dataclass
class DeriveTasksFromPlanUseCase:
    """Use case for automatic task derivation from approved plans.
    
    Flow (Event-Driven):
    1. Fetch plan from storage
    2. Build LLM prompt for task decomposition
    3. Submit to Ray Executor (async, returns immediately)
    4. Return deliberation_id for tracking
    5. Consumer will handle result when agent completes
    
    Following Hexagonal Architecture:
    - Depends ONLY on ports (StoragePort, RayExecutorPort)
    - Infrastructure adapters injected via constructor
    - NO direct infrastructure calls
    - Uses ONLY Value Objects (NO primitives)
    """
    
    storage: StoragePort
    ray_executor: RayExecutorPort
    
    async def execute(self, plan_id: PlanId) -> DeliberationId:
        """Execute task derivation (fire-and-forget).
        
        Args:
            plan_id: Plan to derive tasks from
            
        Returns:
            DeliberationId for tracking the async job
            
        Raises:
            ValueError: If plan not found or invalid
            RayExecutorError: If Ray Executor submission fails
        """
        logger.info(f"Deriving tasks for plan: {plan_id}")
        
        # Step 1: Fetch plan from storage (via port)
        plan = await self.storage.get_plan(plan_id)
        
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")
        
        logger.debug(f"Fetched plan: {plan_id}")
        
        # Step 2: Build LLM prompt for task decomposition
        prompt = self._build_decomposition_prompt(plan)
        
        logger.debug(f"Built prompt: {prompt.token_count_estimate()} tokens (estimated)")
        
        # Step 3: Submit to Ray Executor (async, returns immediately)
        # Ray will execute on GPU worker and publish result to NATS
        role = Role("SYSTEM")  # Task derivation is system-level operation
        
        deliberation_id = await self.ray_executor.submit_task_derivation(
            plan_id=plan_id,
            prompt=prompt,
            role=role,
        )
        
        logger.info(
            f"✅ Task derivation submitted to Ray Executor: {deliberation_id}"
        )
        
        # Step 4: Return immediately (event-driven)
        # Consumer will process result when agent.response.completed arrives
        return deliberation_id
    
    def _build_decomposition_prompt(self, plan) -> LLMPrompt:
        """Build LLM prompt for task decomposition.
        
        Args:
            plan: Plan entity from storage
            
        Returns:
            LLMPrompt value object
        """
        # Extract plan details (via Tell, Don't Ask if available)
        description = str(plan.description) if hasattr(plan, 'description') else ""
        
        # Build structured prompt
        prompt_text = f"""# Task Derivation

Decompose the following software development plan into atomic, executable tasks.

## Plan Description
{description}

## Instructions
For each task, provide:
1. **TASK_ID**: Unique identifier (e.g., TASK-001)
2. **TITLE**: Brief task title (max 80 chars)
3. **DESCRIPTION**: Detailed task description
4. **ROLE**: Assigned role (DEV, QA, ARCHITECT, PO)
5. **ESTIMATED_HOURS**: Estimated hours (integer, 1-40)
6. **PRIORITY**: Priority 1-10 (1 = highest)
7. **KEYWORDS**: Key technical concepts (comma-separated, 2-5 keywords)

## Output Format
Output EXACTLY in this format (one task per block):

```
TASK_ID: TASK-001
TITLE: Setup project structure
DESCRIPTION: Initialize repository with standard directory layout and configuration files
ROLE: DEV
ESTIMATED_HOURS: 2
PRIORITY: 1
KEYWORDS: setup, repository, structure
```

IMPORTANT:
- Derive 3-8 atomic tasks
- Each task should be completable in 1-2 days
- Keywords should be technical concepts (for dependency detection)
- Avoid circular dependencies (if A needs B, B cannot need A)

Derive the tasks now:
"""
        
        return LLMPrompt(prompt_text)

