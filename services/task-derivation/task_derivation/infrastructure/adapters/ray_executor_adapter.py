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

logger = logging.getLogger(__name__)


class RayExecutorAdapter(RayExecutorPort):
    """Concrete adapter for submitting derivation jobs to Ray Executor via gRPC."""

    def __init__(
        self,
        address: str,
        *,
        timeout_seconds: float = 5.0,
    ) -> None:
        """Initialize adapter with Ray Executor address.

        Args:
            address: gRPC service address (e.g., "ray-executor:50055")
            timeout_seconds: Request timeout (short - only submits job, doesn't wait)

        Raises:
            ValueError: If address is empty
        """
        if not address or not address.strip():
            raise ValueError("RayExecutorAdapter address cannot be empty")

        self._address = address
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
                self._channel = aio.secure_channel(
                    self._address,
                    grpc.ssl_channel_credentials(),
                )

            # Create stub on first use
            if self._stub is None:
                self._stub = ray_executor_pb2_grpc.RayExecutorServiceStub(self._channel)

            # Create submission request
            request = ray_executor_pb2.SubmitTaskDerivationRequest(
                plan_id=plan_id.value,
                prompt_text=prompt.value,
                role=role.value,
            )

            # Submit to Ray Executor
            response = await self._stub.SubmitTaskDerivation(
                request, timeout=self._timeout
            )

            request_id = DerivationRequestId(response.derivation_request_id)
            logger.info("Derivation job submitted with request ID: %s", request_id.value)
            return request_id

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

