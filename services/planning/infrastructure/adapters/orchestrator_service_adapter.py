"""OrchestratorServiceAdapter - gRPC client for Orchestrator Service.

Adapter (Infrastructure Layer):
- Implements OrchestratorPort (application layer interface)
- gRPC client for Orchestrator Service
- Converts between domain DTOs and protobuf messages

Following Hexagonal Architecture:
- Infrastructure adapter implementing application port
- Handles gRPC communication details
- Fire-and-forget pattern: returns DeliberationId immediately

Design Pattern:
- Submit deliberation request via gRPC
- Extract execution_id from response metadata
- Return DeliberationId immediately (~30ms)
- Results handled asynchronously via NATS consumer
"""

import logging
import uuid
from dataclasses import dataclass

import grpc
from planning.application.ports.orchestrator_port import (
    DeliberationRequest,
    OrchestratorError,
)
from planning.domain.value_objects.identifiers.deliberation_id import DeliberationId
from planning.gen import orchestrator_pb2_grpc
from planning.infrastructure.mappers.orchestrator_protobuf_mapper import (
    OrchestratorProtobufMapper,
)

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorServiceAdapter:
    """
    gRPC adapter for Orchestrator Service.

    Implements OrchestratorPort using gRPC client with fire-and-forget pattern.

    Configuration:
    - host: Orchestrator Service host (e.g., "orchestrator-service:50055")
    - timeout_seconds: gRPC call timeout (short, just for ACK)

    Design:
    - Submits deliberation request
    - Returns immediately with DeliberationId from response metadata
    - Orchestrator executes asynchronously in Ray cluster
    - Results published to NATS
    """

    host: str
    timeout_seconds: int = 30  # Short timeout for fire-and-forget ACK

    def __post_init__(self) -> None:
        """Initialize gRPC channel and stub."""
        self._channel = grpc.aio.insecure_channel(self.host)
        self._stub = orchestrator_pb2_grpc.OrchestratorServiceStub(self._channel)
        logger.info(f"Orchestrator adapter initialized (fire-and-forget): {self.host}")

    async def deliberate(
        self,
        request: DeliberationRequest,
    ) -> DeliberationId:
        """
        Submit deliberation request to Orchestrator (fire-and-forget).

        This method submits the request and returns immediately with a tracking ID.
        The actual deliberation happens asynchronously in the Ray cluster.

        Args:
            request: Deliberation request (domain DTO)

        Returns:
            DeliberationId for tracking async execution

        Raises:
            OrchestratorError: If gRPC call fails
        """
        try:
            logger.info(
                f"📤 Submitting deliberation: role={request.role}, "
                f"rounds={request.rounds}, agents={request.num_agents}"
            )

            # Convert domain DTO → Protobuf using mapper (infrastructure concern)
            grpc_request = OrchestratorProtobufMapper.to_deliberate_request(request)

            # Call gRPC service (returns immediately with ACK + execution_id)
            grpc_response = await self._stub.Deliberate(
                grpc_request,
                timeout=self.timeout_seconds,
            )

            # Extract execution_id from metadata as tracking ID
            execution_id = grpc_response.metadata.execution_id if grpc_response.metadata else ""

            if not execution_id:
                # Fallback: generate unique ID if no execution_id in response
                execution_id = f"delib-{uuid.uuid4().hex[:8]}"
                logger.warning(f"No execution_id in response, using fallback: {execution_id}")

            deliberation_id = DeliberationId(execution_id)

            logger.info(
                f"✅ Deliberation submitted: {deliberation_id.value} "
                f"(fire-and-forget, results via NATS)"
            )

            return deliberation_id

        except grpc.RpcError as e:
            error_msg = f"Orchestrator gRPC error: {e.code()} - {e.details()}"
            logger.error(error_msg)
            raise OrchestratorError(error_msg) from e

        except Exception as e:
            error_msg = f"Orchestrator error: {e}"
            logger.error(error_msg, exc_info=True)
            raise OrchestratorError(error_msg) from e

    async def close(self) -> None:
        """Close gRPC channel."""
        if self._channel:
            await self._channel.close()
            logger.info("Orchestrator adapter channel closed")




