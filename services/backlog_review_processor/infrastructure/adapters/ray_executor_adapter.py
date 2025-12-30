"""Ray Executor gRPC adapter for Backlog Review Processor Service.

Following Hexagonal Architecture:
- Implements RayExecutorPort (application layer interface)
- Lives in infrastructure layer
- Handles gRPC communication with Ray Executor Service
"""

import logging

import grpc
from backlog_review_processor.application.ports.ray_executor_port import (
    RayExecutorError,
    RayExecutorPort,
)
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.deliberation_id import DeliberationId
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId

# Agent role constants (infrastructure layer - no domain coupling)
TASK_EXTRACTOR_ROLE = "TASK_EXTRACTOR"

# Import protobuf stubs (generated during container build)
# Backlog Review Processor Service will generate these from specs/fleet/ray_executor/v1/ray_executor.proto
try:
    from backlog_review_processor.gen import ray_executor_pb2, ray_executor_pb2_grpc
except ImportError:
    # Fallback for development (protobuf stubs not generated yet)
    ray_executor_pb2 = None
    ray_executor_pb2_grpc = None

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
    - submit_task_extraction() returns immediately
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

        if ray_executor_pb2 is None or ray_executor_pb2_grpc is None:
            raise RuntimeError(
                "Ray Executor protobuf stubs not available. "
                "Generate protobuf stubs before instantiating RayExecutorAdapter."
            )

        self.address = grpc_address
        self.vllm_url = vllm_url
        self.vllm_model = vllm_model
        self.channel = grpc.aio.insecure_channel(grpc_address)
        self.stub = ray_executor_pb2_grpc.RayExecutorServiceStub(self.channel)

        logger.info(f"RayExecutorAdapter initialized: {grpc_address}")

    async def submit_task_extraction(
        self,
        task_id: str,
        task_description: str,
        story_id: StoryId,
        ceremony_id: BacklogReviewCeremonyId,
    ) -> DeliberationId:
        """Submit task extraction job to Ray Executor.

        Fire-and-forget pattern:
        1. Build gRPC request from parameters
        2. Call Ray Executor ExecuteDeliberation (returns immediately)
        3. Return DeliberationId for tracking
        4. Ray executes async with vLLM agent and publishes to NATS

        Args:
            task_id: Task identifier (format: "ceremony-{id}:story-{id}:task-extraction")
            task_description: Prompt with all agent deliberations for task extraction
            story_id: Story identifier
            ceremony_id: Ceremony identifier

        Returns:
            DeliberationId for tracking async job

        Raises:
            RayExecutorError: If gRPC call fails
        """
        try:
            # Build single-agent configuration for task extraction
            agent = ray_executor_pb2.Agent(
                id="agent-task-extractor-001",
                role=TASK_EXTRACTOR_ROLE,
                model=self.vllm_model,
                prompt_template="",  # Prompt is in task_description
            )

            # Build constraints with metadata
            # Include story_id in metadata so TaskExtractionResultConsumer can find it
            constraints = ray_executor_pb2.TaskConstraints(
                story_id=story_id.value,
                timeout_seconds=300,  # 5 minutes default
                max_retries=3,
                metadata={
                    "story_id": story_id.value,  # Required for TaskExtractionResultConsumer
                    "ceremony_id": ceremony_id.value,
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
                vllm_url=self.vllm_url,
                vllm_model=self.vllm_model,
            )

            logger.info(f"📤 Submitting task extraction to Ray Executor: {task_id}")

            # Execute gRPC call (async, returns immediately)
            response = await self.stub.ExecuteDeliberation(request)

            logger.info(
                f"✅ Ray Executor accepted task extraction: {response.deliberation_id} "
                f"(status: {response.status}, task_id: {response.task_id})"
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

    async def close(self) -> None:
        """Close gRPC channel.

        Cleanup method to release resources.
        """
        if self.channel:
            await self.channel.close()
            logger.info(f"Closed gRPC channel to Ray Executor: {self.address}")

