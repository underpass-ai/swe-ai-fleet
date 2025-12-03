"""OrchestratorServiceAdapter - gRPC client for Orchestrator Service.

Adapter (Infrastructure Layer):
- Implements OrchestratorPort (application layer interface)
- gRPC client for Orchestrator Service
- Converts between domain DTOs and protobuf messages

Following Hexagonal Architecture:
- Infrastructure adapter implementing application port
- Handles gRPC communication details
- Converts protobuf ↔ domain DTOs
"""

import logging
from dataclasses import dataclass

import grpc

from planning.application.ports.orchestrator_port import (
    DeliberationRequest,
    DeliberationResponse,
    DeliberationResult,
    OrchestratorError,
    OrchestratorPort,
    Proposal,
    TaskConstraints,
)

# Import generated protobuf code
try:
    from planning.gen import orchestrator_pb2, orchestrator_pb2_grpc
except ImportError:
    # Fallback for different import paths
    from gen import orchestrator_pb2, orchestrator_pb2_grpc

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorServiceAdapter:
    """
    gRPC adapter for Orchestrator Service.

    Implements OrchestratorPort using gRPC client.

    Configuration:
    - host: Orchestrator Service host (e.g., "orchestrator-service:50055")
    - timeout_seconds: gRPC call timeout
    """

    host: str
    timeout_seconds: int = 300  # 5 minutes default

    def __post_init__(self) -> None:
        """Initialize gRPC channel and stub."""
        self._channel = grpc.aio.insecure_channel(self.host)
        self._stub = orchestrator_pb2_grpc.OrchestratorServiceStub(self._channel)
        logger.info(f"Orchestrator adapter initialized: {self.host}")

    async def deliberate(
        self,
        request: DeliberationRequest,
    ) -> DeliberationResponse:
        """
        Execute multi-agent deliberation via Orchestrator Service.

        Args:
            request: Deliberation request (domain DTO)

        Returns:
            DeliberationResponse (domain DTO)

        Raises:
            OrchestratorError: If gRPC call fails
        """
        try:
            logger.info(
                f"Deliberating with role={request.role}, "
                f"rounds={request.rounds}, agents={request.num_agents}"
            )

            # Convert domain DTO → Protobuf
            grpc_request = self._to_grpc_request(request)

            # Call gRPC service
            grpc_response = await self._stub.Deliberate(
                grpc_request,
                timeout=self.timeout_seconds,
            )

            # Convert Protobuf → domain DTO
            response = self._from_grpc_response(grpc_response)

            logger.info(
                f"Deliberation completed: winner={response.winner_id}, "
                f"duration={response.duration_ms}ms"
            )

            return response

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

    def _to_grpc_request(
        self,
        request: DeliberationRequest,
    ) -> orchestrator_pb2.DeliberateRequest:
        """Convert domain DTO to protobuf message."""
        # Build TaskConstraints if provided
        constraints = None
        if request.constraints:
            constraints = orchestrator_pb2.TaskConstraints(
                rubric=request.constraints.rubric,
                requirements=list(request.constraints.requirements),
                metadata=request.constraints.metadata or {},
                max_iterations=request.constraints.max_iterations,
                timeout_seconds=request.constraints.timeout_seconds,
            )

        return orchestrator_pb2.DeliberateRequest(
            task_description=request.task_description,
            role=request.role,
            constraints=constraints,
            rounds=request.rounds,
            num_agents=request.num_agents,
        )

    def _from_grpc_response(
        self,
        grpc_response: orchestrator_pb2.DeliberateResponse,
    ) -> DeliberationResponse:
        """Convert protobuf message to domain DTO."""
        # Convert results
        results = tuple(
            self._convert_deliberation_result(result)
            for result in grpc_response.results
        )

        return DeliberationResponse(
            results=results,
            winner_id=grpc_response.winner_id,
            duration_ms=grpc_response.duration_ms,
        )

    def _convert_deliberation_result(
        self,
        pb_result: orchestrator_pb2.DeliberationResult,
    ) -> DeliberationResult:
        """Convert protobuf DeliberationResult to domain DTO."""
        # Convert proposal
        proposal = Proposal(
            author_id=pb_result.proposal.author_id,
            author_role=pb_result.proposal.author_role,
            content=pb_result.proposal.content,
            created_at_ms=pb_result.proposal.created_at_ms,
            revisions=tuple(pb_result.proposal.revisions),
        )

        # Extract checks_passed from CheckSuite
        checks_passed = pb_result.checks.all_passed if pb_result.checks else False

        return DeliberationResult(
            proposal=proposal,
            checks_passed=checks_passed,
            score=pb_result.score,
            rank=pb_result.rank,
        )



