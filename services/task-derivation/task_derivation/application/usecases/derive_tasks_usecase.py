"""DeriveTasksUseCase orchestrates LLM prompt submission."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from task_derivation.application.ports.context_port import ContextPort
from task_derivation.application.ports.planning_port import PlanningPort
from task_derivation.application.ports.ray_executor_port import RayExecutorPort
from task_derivation.domain.value_objects.content.acceptance_criteria import (
    AcceptanceCriteria,
)
from task_derivation.domain.value_objects.task_derivation.config.task_derivation_config import (
    TaskDerivationConfig,
)
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.domain.value_objects.task_derivation.context.derivation_phase import (
    DerivationPhase,
)
from task_derivation.domain.value_objects.task_derivation.context.plan_context import (
    PlanContext,
)
from task_derivation.domain.value_objects.task_derivation.prompt.llm_prompt import (
    LLMPrompt,
)
from task_derivation.domain.value_objects.task_derivation.requests.derivation_request_id import (
    DerivationRequestId,
)
from task_derivation.domain.value_objects.task_derivation.requests.task_derivation_request import (
    TaskDerivationRequest,
)
from task_derivation.domain.value_objects.task_derivation.roles.executor_role import (
    ExecutorRole,
)

logger = logging.getLogger(__name__)


@dataclass
class DeriveTasksUseCase:
    """Fetch plan/context, craft prompt, and submit to Ray."""

    planning_port: PlanningPort
    context_port: ContextPort
    ray_executor_port: RayExecutorPort
    config: TaskDerivationConfig
    executor_role: ExecutorRole = field(
        default_factory=lambda: ExecutorRole("SYSTEM")
    )

    async def execute(self, request: TaskDerivationRequest) -> DerivationRequestId:
        """Handle a task derivation request."""
        logger.info(
            "Starting task derivation for plan %s / story %s",
            request.plan_id.value,
            request.story_id.value,
        )

        plan_context = await self.planning_port.get_plan(request.plan_id)
        context_role = self._select_role(request, plan_context)

        rehydrated_context = await self._fetch_context(request.story_id, context_role)

        prompt = self._build_prompt(plan_context, rehydrated_context)

        request_id = await self.ray_executor_port.submit_task_derivation(
            plan_id=request.plan_id,
            prompt=prompt,
            role=self.executor_role,
        )

        logger.info(
            "Submitted derivation job %s for plan %s",
            request_id.value,
            request.plan_id.value,
        )
        return request_id

    def _select_role(
        self,
        request: TaskDerivationRequest,
        plan_context: PlanContext,
    ) -> ContextRole:
        if request.roles:
            return request.roles[0]
        return plan_context.roles[0]

    async def _fetch_context(
        self,
        story_id,
        role: ContextRole,
    ) -> str | None:
        try:
            return await self.context_port.get_context(
                story_id=story_id,
                role=role,
                phase=DerivationPhase.PLAN,
            )
        except Exception as exc:  # pragma: no cover - fallback path
            logger.warning(
                "Failed to fetch rehydrated context for story %s (%s)",
                story_id.value,
                exc,
            )
            return None

    def _build_prompt(
        self,
        plan_context: PlanContext,
        rehydrated_context: str | None,
    ) -> LLMPrompt:
        description = plan_context.description.value
        acceptance_criteria = self._format_acceptance_criteria(
            plan_context.acceptance_criteria
        )
        technical_notes = plan_context.technical_notes.value

        prompt_text = self.config.build_prompt(
            description=description,
            acceptance_criteria=acceptance_criteria,
            technical_notes=technical_notes,
            rehydrated_context=rehydrated_context,
        )
        return LLMPrompt(prompt_text)

    @staticmethod
    def _format_acceptance_criteria(criteria: AcceptanceCriteria) -> str:
        return "\n".join(f"- {criterion}" for criterion in criteria)

