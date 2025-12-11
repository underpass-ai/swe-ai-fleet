"""Mapper for Ray Executor gRPC requests and responses.

Infrastructure Mapper:
- Converts domain VOs ↔ protobuf messages
- Lives in infrastructure layer
- Handles external format conversions
"""

from planning.domain.value_objects.actors.role import Role
from planning.domain.value_objects.health_status import HealthStatus
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.task_derivation.llm_prompt import LLMPrompt
from planning.gen import ray_executor_pb2

# Agent role constants (infrastructure layer - no domain coupling)
TASK_EXTRACTOR_ROLE = "TASK_EXTRACTOR"


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
        role: Role,
        vllm_url: str,
        vllm_model: str,
    ) -> ray_executor_pb2.ExecuteDeliberationRequest:
        """Map domain VOs to ExecuteDeliberationRequest protobuf.

        Args:
            plan_id: Plan identifier (domain VO)
            prompt: LLM prompt (domain VO)
            role: Role context (domain VO)
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
            role=str(role),  # VO → string at boundary
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
            role=str(role),
            constraints=constraints,
            agents=[agent],
            vllm_url=vllm_url,
            vllm_model=vllm_model,
        )

    @staticmethod
    def to_execute_backlog_review_deliberation_request(
        task_id: str,
        task_description: str,
        role: str,
        story_id: str,
        num_agents: int,
        vllm_url: str,
        vllm_model: str,
    ) -> ray_executor_pb2.ExecuteBacklogReviewDeliberationRequest:
        """Map domain parameters to ExecuteBacklogReviewDeliberationRequest protobuf.

        Args:
            task_id: Task identifier (format: "ceremony-{id}:story-{id}:role-{role}")
            task_description: Task description with context embedded
            role: Role for the deliberation (e.g., "ARCHITECT", "QA", "DEVOPS")
            story_id: Story identifier
            num_agents: Number of agents to use
            vllm_url: vLLM service URL
            vllm_model: Model name

        Returns:
            Protobuf request message for backlog review deliberation
        """
        # Build agents list (multiple agents for diversity)
        agents = []
        for i in range(num_agents):
            agent = ray_executor_pb2.Agent(
                id=f"agent-{role.lower()}-{i+1:03d}",
                role=role,
                model=vllm_model,
                prompt_template="",  # Direct prompt, no template
            )
            agents.append(agent)

        # Build backlog review task constraints (no plan_id required)
        constraints = ray_executor_pb2.BacklogReviewTaskConstraints(
            story_id=story_id,
            timeout_seconds=300,  # 5 minutes default
            max_retries=3,
            metadata={"task_id": task_id},  # Include original task_id in metadata
        )

        # Build protobuf request
        return ray_executor_pb2.ExecuteBacklogReviewDeliberationRequest(
            task_id=task_id,
            task_description=task_description,
            role=role,
            constraints=constraints,
            agents=agents,
            vllm_url=vllm_url,
            vllm_model=vllm_model,
        )

    @staticmethod
    def from_get_status_response(
        response: ray_executor_pb2.GetStatusResponse
    ) -> HealthStatus:
        """Map GetStatusResponse protobuf to HealthStatus VO.

        Args:
            response: Protobuf response from Ray Executor

        Returns:
            HealthStatus enum value
        """
        # Map string to enum (protobuf → domain)
        status_str = response.status.lower()

        if status_str == "healthy":
            return HealthStatus.HEALTHY
        elif status_str == "unhealthy":
            return HealthStatus.UNHEALTHY
        elif status_str == "degraded":
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNKNOWN

    @staticmethod
    def to_execute_deliberation_request_for_backlog_review_processor(
        task_id: str,
        task_description: str,
        story_id: str,
        ceremony_id: str,
        vllm_url: str,
        vllm_model: str,
    ) -> ray_executor_pb2.ExecuteDeliberationRequest:
        """Map parameters to ExecuteDeliberationRequest for task extraction.

        Creates a single-agent configuration for task extraction from deliberations.

        Args:
            task_id: Task identifier (format: "ceremony-{id}:story-{id}:task-extraction")
            task_description: Prompt with all agent deliberations
            story_id: Story identifier
            ceremony_id: Ceremony identifier
            vllm_url: vLLM service URL
            vllm_model: Model name

        Returns:
            Protobuf request message
        """
        # Build single-agent configuration for task extraction
        agent = ray_executor_pb2.Agent(
            id="agent-task-extractor-001",
            role=TASK_EXTRACTOR_ROLE,
            model=vllm_model,
            prompt_template="",  # Prompt is in task_description
        )

        # Build constraints with metadata
        constraints = ray_executor_pb2.TaskConstraints(
            story_id=story_id,
            timeout_seconds=300,  # 5 minutes default
            max_retries=3,
            metadata={
                "ceremony_id": ceremony_id,
                "task_type": "TASK_EXTRACTION",
            },
        )

        # Build request
        request = ray_executor_pb2.ExecuteDeliberationRequest(
            task_id=task_id,
            task_description=task_description,
            role=TASK_EXTRACTOR_ROLE,  # Required field
            agents=[agent],
            constraints=constraints,
            vllm_url=vllm_url,
            vllm_model=vllm_model,
        )

        return request

