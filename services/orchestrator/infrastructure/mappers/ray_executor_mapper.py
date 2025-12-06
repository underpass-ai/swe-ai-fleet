"""Mapper for Ray Executor infrastructure."""

from __future__ import annotations

from typing import Any

from services.orchestrator.domain.entities import (
    DeliberationStatus,
    DeliberationSubmission,
)
from services.orchestrator.gen import ray_executor_pb2


class RayExecutorMapper:
    """Mapper for Ray Executor gRPC messages.

    Handles conversion between domain objects/dictionaries and
    Ray Executor protobuf messages.
    """

    @staticmethod
    def to_execute_request(
        task_id: str,
        task_description: str,
        role: str,
        agents: list[dict[str, Any]],
        constraints: dict[str, Any],
        vllm_url: str,
        vllm_model: str,
    ) -> ray_executor_pb2.ExecuteDeliberationRequest:
        """Convert domain objects to ExecuteDeliberationRequest.

        Args:
            task_id: ID of the task
            task_description: Description of the task
            role: Role required for the task
            agents: List of agent configurations
            constraints: Task constraints
            vllm_url: URL for vLLM service
            vllm_model: Model to use

        Returns:
            Protobuf request message
        """
        # Build agents list for proto
        proto_agents = []
        for agent in agents:
            proto_agent = ray_executor_pb2.Agent(
                id=agent["id"],
                role=agent["role"],
                model=agent.get("model", vllm_model),
                prompt_template=agent.get("prompt_template", "")
            )
            proto_agents.append(proto_agent)

        # Build constraints for proto
        task_constraints = ray_executor_pb2.TaskConstraints(
            story_id=constraints.get("story_id", ""),
            plan_id=constraints.get("plan_id", ""),
            timeout_seconds=constraints.get("timeout", 300),
            max_retries=constraints.get("max_retries", 3)
        )

        # Build request
        return ray_executor_pb2.ExecuteDeliberationRequest(
            task_id=task_id,
            task_description=task_description,
            role=role,
            constraints=task_constraints,
            agents=proto_agents,
            vllm_url=vllm_url,
            vllm_model=vllm_model
        )

    @staticmethod
    def to_deliberation_submission(
        response: ray_executor_pb2.ExecuteDeliberationResponse
    ) -> DeliberationSubmission:
        """Convert ExecuteDeliberationResponse to DeliberationSubmission entity.

        Args:
            response: Protobuf response message

        Returns:
            DeliberationSubmission domain entity
        """
        return DeliberationSubmission(
            deliberation_id=response.deliberation_id,
            status=response.status,
            message=response.message,
        )

    @staticmethod
    def to_get_status_request(
        deliberation_id: str
    ) -> ray_executor_pb2.GetDeliberationStatusRequest:
        """Create GetDeliberationStatusRequest.

        Args:
            deliberation_id: ID of the deliberation

        Returns:
            Protobuf request message
        """
        return ray_executor_pb2.GetDeliberationStatusRequest(
            deliberation_id=deliberation_id
        )

    @staticmethod
    def to_deliberation_status(
        deliberation_id: str,
        response: ray_executor_pb2.GetDeliberationStatusResponse
    ) -> DeliberationStatus:
        """Convert GetDeliberationStatusResponse to DeliberationStatus entity.

        Args:
            deliberation_id: ID of the deliberation
            response: Protobuf response message

        Returns:
            DeliberationStatus domain entity
        """
        result_data = None
        if response.HasField("result"):
            result_data = response.result

        return DeliberationStatus(
            deliberation_id=deliberation_id,
            status=response.status,
            result=result_data,
            error_message=response.error_message if response.error_message else None
        )

