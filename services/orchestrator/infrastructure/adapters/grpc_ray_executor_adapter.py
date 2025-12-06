"""gRPC adapter for Ray Executor communication."""

from __future__ import annotations

import logging
from typing import Any

import grpc
from services.orchestrator.domain.entities import (
    DeliberationStatus,
    DeliberationSubmission,
)
from services.orchestrator.domain.ports import RayExecutorPort
from services.orchestrator.gen import ray_executor_pb2_grpc
from services.orchestrator.infrastructure.mappers.ray_executor_mapper import (
    RayExecutorMapper,
)

logger = logging.getLogger(__name__)


class GRPCRayExecutorAdapter(RayExecutorPort):
    """Adapter implementing Ray Executor communication via gRPC.

    This adapter implements the RayExecutorPort interface using gRPC,
    keeping infrastructure concerns separated from domain logic.

    Attributes:
        address: Ray Executor gRPC address
        channel: gRPC async channel
        stub: Ray Executor gRPC stub
    """

    def __init__(self, address: str):
        """Initialize gRPC Ray Executor adapter.

        Args:
            address: Ray Executor service address (e.g., "localhost:50056")
        """
        self.address = address
        self.channel = grpc.aio.insecure_channel(address)
        self.stub = ray_executor_pb2_grpc.RayExecutorServiceStub(self.channel)

        logger.info(f"GRPCRayExecutorAdapter initialized: {address}")

    async def execute_deliberation(
        self,
        task_id: str,
        task_description: str,
        role: str,
        agents: list[dict[str, Any]],
        constraints: dict[str, Any],
        vllm_url: str,
        vllm_model: str,
    ) -> DeliberationSubmission:
        """Execute deliberation on Ray cluster via gRPC.

        Implements RayExecutorPort.execute_deliberation using gRPC.
        Returns DeliberationSubmission entity instead of dict.
        """
        try:
            # Build request using mapper
            request = RayExecutorMapper.to_execute_request(
                task_id=task_id,
                task_description=task_description,
                role=role,
                agents=agents,
                constraints=constraints,
                vllm_url=vllm_url,
                vllm_model=vllm_model,
            )

            # Execute gRPC call
            response = await self.stub.ExecuteDeliberation(request)

            logger.info(
                f"✅ Ray Executor accepted deliberation: {response.deliberation_id} "
                f"(status: {response.status})"
            )

            # Return domain entity using mapper
            return RayExecutorMapper.to_deliberation_submission(response)

        except Exception as e:
            logger.error(f"❌ Failed to submit deliberation to Ray Executor: {e}")
            raise

    async def get_deliberation_status(
        self,
        deliberation_id: str,
    ) -> DeliberationStatus:
        """Get deliberation status via gRPC.

        Implements RayExecutorPort.get_deliberation_status using gRPC.
        Returns DeliberationStatus entity instead of dict.
        """
        try:
            # Build request using mapper
            request = RayExecutorMapper.to_get_status_request(deliberation_id)

            response = await self.stub.GetDeliberationStatus(request)

            # Return domain entity using mapper
            return RayExecutorMapper.to_deliberation_status(deliberation_id, response)

        except Exception as e:
            logger.error(f"Failed to get deliberation status: {e}")
            raise

    async def close(self) -> None:
        """Close gRPC channel.

        Implements RayExecutorPort.close to release resources.
        """
        if self.channel:
            await self.channel.close()
            logger.info(f"Closed gRPC channel to Ray Executor: {self.address}")

    def __repr__(self) -> str:
        """String representation."""
        return f"GRPCRayExecutorAdapter(address={self.address})"

