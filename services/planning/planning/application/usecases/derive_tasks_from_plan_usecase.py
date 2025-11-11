"""DeriveTasksFromPlanUseCase - Automatic task derivation using LLM.

Use Case (Application Layer):
- Orchestrates domain logic
- Depends on ports (interfaces)
- NO infrastructure dependencies
- Event-driven (fire-and-forget)
- Configuration externalized (YAML)
"""

import logging
from dataclasses import dataclass

from planning.application.ports import RayExecutorPort, StoragePort
from planning.domain.entities.plan import Plan
from planning.domain.value_objects.actors.role import Role
from planning.domain.value_objects.identifiers.deliberation_id import DeliberationId
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.task_derivation.llm_prompt import LLMPrompt
from planning.domain.value_objects.task_derivation.task_derivation_config import (
    TaskDerivationConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class DeriveTasksFromPlanUseCase:
    """Use case for automatic task derivation from approved plans.

    Flow (Event-Driven):
    1. Fetch plan from storage
    2. Build LLM prompt from config template
    3. Submit to Ray Executor (async, returns immediately)
    4. Return deliberation_id for tracking
    5. Consumer will handle result when agent completes

    Following Hexagonal Architecture:
    - Depends ONLY on ports (StoragePort, RayExecutorPort)
    - Infrastructure adapters injected via constructor
    - NO direct infrastructure calls
    - Uses ONLY Value Objects (NO primitives)
    - Configuration externalized (config/task_derivation.yaml)
    """

    storage: StoragePort
    ray_executor: RayExecutorPort
    config: TaskDerivationConfig  # Injected configuration

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
        role = Role.system()  # Task derivation is system-level operation

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

    def _build_decomposition_prompt(self, plan: Plan) -> LLMPrompt:
        """Build LLM prompt from config template.

        Tell, Don't Ask: Plan provides content, Config builds prompt.
        NO reflexión (hasattr) - Plan entity tiene contrato claro.

        Args:
            plan: Plan entity from storage

        Returns:
            LLMPrompt value object
        """
        # Tell, Don't Ask: Plan provides its content
        description = plan.get_description_for_decomposition()
        acceptance_criteria = plan.get_acceptance_criteria_text()
        technical_notes = plan.get_technical_notes_text()

        # Tell, Don't Ask: Config builds prompt from template
        prompt_text = self.config.build_prompt(
            description=description,
            acceptance_criteria=acceptance_criteria,
            technical_notes=technical_notes,
        )

        return LLMPrompt(prompt_text)

