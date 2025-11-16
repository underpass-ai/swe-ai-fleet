"""Ray Executor gRPC adapter for Planning Service.

Following Hexagonal Architecture:
- Implements RayExecutorPort (application layer interface)
- Lives in infrastructure layer
- Handles gRPC communication with Ray Executor Service
"""

import logging

import grpc

# Import protobuf stubs (generated during container build)
# Planning Service will generate these from specs/fleet/ray_executor/v1/ray_executor.proto
from services.planning.gen import ray_executor_pb2, ray_executor_pb2_grpc

from planning.application.ports.ray_executor_port import (
    RayExecutorError,
    RayExecutorPort,
)
from planning.domain.value_objects.actors.role import Role
from planning.domain.value_objects.identifiers.deliberation_id import DeliberationId
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.task_derivation.llm_prompt import LLMPrompt
from planning.infrastructure.mappers.ray_executor_request_mapper import (
    RayExecutorRequestMapper,
)

logger = logging.getLogger(__name__)


class RayExecutorAdapter(RayExecutorPort):
    """gRPC adapter for Ray Executor communication.

    Adapter responsibilities:
    - Connect to Ray Executor Service via gRPC
    - Implement RayExecutorPort interface
    - Map domain VOs to protobuf messages
    - Map protobuf responses to domain VOs
    - Handle gRPC errors

    Following Hexagonal Architecture:
    - Implements port (interface) from application layer
    - Uses gRPC client (infrastructure detail)
    - Fail-fast on configuration errors

    Design: Event-Driven
    - submit_task_derivation() returns immediately
    - Ray executes asynchronously
    - Result comes via NATS (not through this adapter)
    """

    def __init__(
        self,
        grpc_address: str,
        vllm_url: str,
        vllm_model: str,
    ):
        """Initialize adapter with gRPC configuration.

        Args:
            grpc_address: Ray Executor service address (e.g., "ray-executor:50056")
            vllm_url: vLLM service URL for Ray workers
            vllm_model: Model name to use

        Raises:
            ValueError: If any parameter is invalid
        """
        if not grpc_address or not grpc_address.strip():
            raise ValueError("grpc_address cannot be empty")
        if not vllm_url or not vllm_url.strip():
            raise ValueError("vllm_url cannot be empty")
        if not vllm_model or not vllm_model.strip():
            raise ValueError("vllm_model cannot be empty")

        self.address = grpc_address
        self.vllm_url = vllm_url
        self.vllm_model = vllm_model
        self.channel = grpc.aio.insecure_channel(grpc_address)
        self.stub = ray_executor_pb2_grpc.RayExecutorServiceStub(self.channel)

        logger.info(f"RayExecutorAdapter initialized: {grpc_address}")

    async def submit_task_derivation(
        self,
        plan_id: PlanId,
        prompt: LLMPrompt,
        role: Role,
    ) -> DeliberationId:
        """Submit task derivation job to Ray Executor.

        Fire-and-forget pattern:
        1. Build gRPC request from domain VOs
        2. Call Ray Executor (returns immediately)
        3. Return DeliberationId for tracking
        4. Ray executes async and publishes to NATS

        Args:
            plan_id: Plan identifier
            prompt: LLM prompt for task decomposition
            role: Role context for generation

        Returns:
            DeliberationId for tracking async job

        Raises:
            RayExecutorError: If gRPC call fails
        """
        try:
            # Delegate VO → protobuf mapping to mapper (separation of concerns)
            request = RayExecutorRequestMapper.to_execute_deliberation_request(
                plan_id=plan_id,
                prompt=prompt,
                role=role,
                vllm_url=self.vllm_url,
                vllm_model=self.vllm_model,
            )

            logger.info(f"📤 Submitting task derivation to Ray Executor: {request.task_id}")

            # Execute gRPC call (async, returns immediately)
            response = await self.stub.ExecuteDeliberation(request)

            logger.info(
                f"✅ Ray Executor accepted: {response.deliberation_id} "
                f"(status: {response.status})"
            )

            # Map protobuf response to domain VO
            return DeliberationId(response.deliberation_id)

        except grpc.RpcError as e:
            error_msg = f"gRPC error calling Ray Executor: {e.code()} - {e.details()}"
            logger.error(error_msg)
            raise RayExecutorError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error calling Ray Executor: {e}"
            logger.error(error_msg, exc_info=True)
            raise RayExecutorError(error_msg) from e

    async def health_check(self) -> bool:
        """Check if Ray Executor is healthy.

        Returns:
            True if Ray Executor is reachable
        """
        try:
            # Call GetStatus (health check endpoint)
            request = ray_executor_pb2.GetStatusRequest()
            response = await self.stub.GetStatus(request, timeout=5)

            # Map protobuf response to domain VO (via mapper)
            status = RayExecutorRequestMapper.from_get_status_response(response)

            logger.debug(f"Ray Executor health check: {status}")

            # Tell, Don't Ask: HealthStatus knows if it's healthy
            return status.is_healthy()

        except Exception as e:
            logger.warning(f"Ray Executor health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close gRPC channel.

        Cleanup method to release resources.
        """
        if self.channel:
            await self.channel.close()
            logger.info(f"Closed gRPC channel to Ray Executor: {self.address}")

