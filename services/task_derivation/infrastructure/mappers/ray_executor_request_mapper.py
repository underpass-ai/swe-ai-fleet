"""Mapper for Ray Executor gRPC requests and responses.

Infrastructure Mapper:
- Converts domain VOs ↔ protobuf messages
- Lives in infrastructure layer
- Handles external format conversions
"""

from __future__ import annotations

from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.task_derivation.prompt.llm_prompt import (
    LLMPrompt,
)
from task_derivation.domain.value_objects.task_derivation.roles.executor_role import (
    ExecutorRole,
)
from task_derivation.gen import ray_executor_pb2


class RayExecutorRequestMapper:
    """Mapper for Ray Executor protobuf requests.

    Following Hexagonal Architecture:
    - Lives in infrastructure layer
    - Converts domain VOs to external format (protobuf)
    - NO business logic - only translation
    - Stateless (all static methods)
    """

    @staticmethod
    def to_execute_deliberation_request(
        plan_id: PlanId,
        prompt: LLMPrompt,
        role: ExecutorRole,
        vllm_url: str,
        vllm_model: str,
    ) -> ray_executor_pb2.ExecuteDeliberationRequest:
        """Map domain VOs to ExecuteDeliberationRequest protobuf.

        Args:
            plan_id: Plan identifier (domain VO)
            prompt: LLM prompt (domain VO)
            role: Executor role (domain VO)
            vllm_url: vLLM service URL
            vllm_model: Model name

        Returns:
            Protobuf request message
        """
        # Build task_id for tracking
        task_id = f"derive-{plan_id.value}"

        # Build single-agent configuration for task derivation
        agent = ray_executor_pb2.Agent(
            id="task-deriver-001",
            role=role.value,  # VO → string at boundary
            model=vllm_model,
            prompt_template="",  # Direct prompt, no template
        )

        # Build task constraints
        constraints = ray_executor_pb2.TaskConstraints(
            story_id="",  # Not applicable for task derivation
            plan_id=plan_id.value,  # VO → string at boundary
            timeout_seconds=120,  # 2 minutes for LLM generation
            max_retries=2,
        )

        # Build protobuf request
        return ray_executor_pb2.ExecuteDeliberationRequest(
            task_id=task_id,
            task_description=prompt.value,  # VO → string at boundary
            role=role.value,
            constraints=constraints,
            agents=[agent],
            vllm_url=vllm_url,
            vllm_model=vllm_model,
        )



