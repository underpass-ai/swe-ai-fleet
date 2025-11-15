"""Port definition for submitting derivation jobs to Ray Executor."""

from __future__ import annotations

from typing import Protocol

from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.task_derivation.requests.derivation_request_id import (
    DerivationRequestId,
)
from task_derivation.domain.value_objects.task_derivation.roles.executor_role import (
    ExecutorRole,
)
from task_derivation.domain.value_objects.task_derivation.prompt.llm_prompt import (
    LLMPrompt,
)


class RayExecutorPort(Protocol):
    """Submits prompts to GPU workers and returns derivation request IDs."""

    async def submit_task_derivation(
        self,
        plan_id: PlanId,
        prompt: LLMPrompt,
        role: ExecutorRole,
    ) -> DerivationRequestId:
        """Submit derivation job and return Ray tracking identifier."""
        ...

