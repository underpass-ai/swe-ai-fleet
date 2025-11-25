"""gRPC adapter for Ray Executor, implementing RayExecutorPort."""

from __future__ import annotations

import logging
from typing import Any

import grpc
from grpc import aio

from task_derivation.application.ports.ray_executor_port import RayExecutorPort
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.task_derivation.prompt.llm_prompt import (
    LLMPrompt,
)
from task_derivation.domain.value_objects.task_derivation.requests.derivation_request_id import (
    DerivationRequestId,
)
from task_derivation.domain.value_objects.task_derivation.roles.executor_role import (
    ExecutorRole,
)
from task_derivation.gen import ray_executor_pb2, ray_executor_pb2_grpc
from task_derivation.infrastructure.mappers.ray_executor_request_mapper import (
    RayExecutorRequestMapper,
)

logger = logging.getLogger(__name__)


class RayExecutorAdapter(RayExecutorPort):
    """Concrete adapter for submitting derivation jobs to Ray Executor via gRPC."""

    def __init__(
        self,
        address: str,
        vllm_url: str,
        vllm_model: str,
        *,
        timeout_seconds: float = 5.0,
    ) -> None:
        """Initialize adapter with Ray Executor address and vLLM configuration.

        Args:
            address: gRPC service address (e.g., "ray-executor:50055")
            vllm_url: vLLM service URL
            vllm_model: Model name for vLLM
            timeout_seconds: Request timeout (short - only submits job, doesn't wait)

        Raises:
            ValueError: If address, vllm_url, or vllm_model is empty
        """
        if not address or not address.strip():
            raise ValueError("RayExecutorAdapter address cannot be empty")
        if not vllm_url or not vllm_url.strip():
            raise ValueError("RayExecutorAdapter vllm_url cannot be empty")
        if not vllm_model or not vllm_model.strip():
            raise ValueError("RayExecutorAdapter vllm_model cannot be empty")

        self._address = address
        self._vllm_url = vllm_url
        self._vllm_model = vllm_model
        self._timeout = timeout_seconds
        self._stub: Any = None
        self._channel: aio.Channel | None = None

    async def submit_task_derivation(
        self,
        plan_id: PlanId,
        prompt: LLMPrompt,
        role: ExecutorRole,
    ) -> DerivationRequestId:
        """Submit derivation job to Ray Executor and return tracking ID.

        Fire-and-forget pattern:
        1. Submits job to Ray Executor (gRPC)
        2. Returns DerivationRequestId immediately
        3. Ray executes asynchronously
        4. Result published to NATS (not returned here)

        Args:
            plan_id: Plan identifier (becomes part of job ID)
            prompt: LLM prompt for task decomposition
            role: Executor role (e.g., SYSTEM for task derivation)

        Returns:
            Unique derivation request ID for result polling

        Raises:
            grpc.RpcError: If service call fails
        """
        try:
            logger.info(
                "Submitting derivation job for plan %s to Ray Executor",
                plan_id.value,
            )

            # Lazy initialization: create channel on first use
            if self._channel is None:
                # Use insecure channel for internal K8s communication
                self._channel = aio.insecure_channel(self._address)

            # Create stub on first use
            if self._stub is None:
                self._stub = ray_executor_pb2_grpc.RayExecutorServiceStub(self._channel)

            # Delegate VO → protobuf mapping to mapper (separation of concerns)
            request = RayExecutorRequestMapper.to_execute_deliberation_request(
                plan_id=plan_id,
                prompt=prompt,
                role=role,
                vllm_url=self._vllm_url,
                vllm_model=self._vllm_model,
            )

            logger.info(
                "📤 Submitting task derivation to Ray Executor: %s", request.task_id
            )

            # Execute gRPC call (async, returns immediately)
            response = await self._stub.ExecuteDeliberation(
                request, timeout=self._timeout
            )

            logger.info(
                "✅ Ray Executor accepted: %s (status: %s)",
                response.deliberation_id,
                response.status,
            )

            # Map protobuf response to domain VO
            # deliberation_id from Ray Executor becomes DerivationRequestId
            request_id = DerivationRequestId(response.deliberation_id)
            logger.info(
                "Derivation job submitted with request ID: %s", request_id.value
            )
            return request_id

        except grpc.RpcError as e:
            error_msg = (
                f"gRPC error calling Ray Executor: {e.code()} - {e.details()}"
            )
            logger.error(error_msg)
            raise

        except Exception as exc:
            logger.error(
                "Failed to submit derivation job for plan %s: %s",
                plan_id.value,
                exc,
                exc_info=True,
            )
            raise

    async def close(self) -> None:
        """Close gRPC channel if open."""
        if self._channel:
            await self._channel.close()
            self._channel = None
            logger.info("RayExecutorAdapter channel closed")
