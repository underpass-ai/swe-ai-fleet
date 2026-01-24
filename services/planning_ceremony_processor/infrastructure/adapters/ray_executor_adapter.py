"""Ray Executor gRPC adapter for planning ceremony processor."""

import logging

import grpc
from core.ceremony_engine.application.ports.deliberation_port import DeliberationPort
from core.ceremony_engine.application.ports.task_extraction_port import TaskExtractionPort

TASK_EXTRACTOR_ROLE = "TASK_EXTRACTOR"

try:
    from services.planning_ceremony_processor.gen import ray_executor_pb2, ray_executor_pb2_grpc
except ImportError:
    ray_executor_pb2 = None
    ray_executor_pb2_grpc = None

logger = logging.getLogger(__name__)


class RayExecutorAdapter(DeliberationPort, TaskExtractionPort):
    """gRPC adapter implementing deliberation and task extraction ports."""

    def __init__(self, grpc_address: str, vllm_url: str, vllm_model: str) -> None:
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

        self._address = grpc_address
        self._vllm_url = vllm_url
        self._vllm_model = vllm_model
        self._channel = grpc.aio.insecure_channel(grpc_address)
        self._stub = ray_executor_pb2_grpc.RayExecutorServiceStub(self._channel)

        logger.info(f"RayExecutorAdapter initialized: {grpc_address}")

    async def submit_backlog_review_deliberation(
        self,
        task_id: str,
        task_description: str,
        role: str,
        story_id: str,
        num_agents: int,
        constraints: dict[str, object] | None = None,
    ) -> str:
        if num_agents <= 0:
            raise ValueError("num_agents must be positive")

        agents = [
            ray_executor_pb2.Agent(
                id=f"agent-{role.lower()}-{i+1:03d}",
                role=role,
                model=self._vllm_model,
                prompt_template="",
            )
            for i in range(num_agents)
        ]

        metadata = {}
        if constraints:
            for key, value in constraints.items():
                metadata[str(key)] = str(value)

        request = ray_executor_pb2.ExecuteBacklogReviewDeliberationRequest(
            task_id=task_id,
            task_description=task_description,
            role=role,
            agents=agents,
            constraints=ray_executor_pb2.BacklogReviewTaskConstraints(
                story_id=story_id,
                timeout_seconds=300,
                max_retries=3,
                metadata=metadata,
            ),
            vllm_url=self._vllm_url,
            vllm_model=self._vllm_model,
        )

        try:
            response = await self._stub.ExecuteBacklogReviewDeliberation(request)
            return response.deliberation_id
        except grpc.RpcError as exc:
            raise RuntimeError(
                f"gRPC error calling Ray Executor: {exc.code()} - {exc.details()}"
            ) from exc

    async def submit_task_extraction(
        self,
        task_id: str,
        task_description: str,
        story_id: str,
        ceremony_id: str,
    ) -> str:
        agent = ray_executor_pb2.Agent(
            id="agent-task-extractor-001",
            role=TASK_EXTRACTOR_ROLE,
            model=self._vllm_model,
            prompt_template="",
        )

        request = ray_executor_pb2.ExecuteDeliberationRequest(
            task_id=task_id,
            task_description=task_description,
            role=TASK_EXTRACTOR_ROLE,
            agents=[agent],
            constraints=ray_executor_pb2.TaskConstraints(
                story_id=story_id,
                plan_id="",
                timeout_seconds=300,
                max_retries=3,
                metadata={"ceremony_id": ceremony_id, "task_type": "TASK_EXTRACTION"},
            ),
            vllm_url=self._vllm_url,
            vllm_model=self._vllm_model,
        )

        try:
            response = await self._stub.ExecuteDeliberation(request)
            return response.deliberation_id
        except grpc.RpcError as exc:
            raise RuntimeError(
                f"gRPC error calling Ray Executor: {exc.code()} - {exc.details()}"
            ) from exc

    async def close(self) -> None:
        if self._channel:
            await self._channel.close()
