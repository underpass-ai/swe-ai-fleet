"""Context Service gRPC adapter for Planning Service.

Infrastructure Adapter (Hexagonal Architecture):
- Implements ContextPort interface
- Calls Context Service via gRPC
- Converts domain VOs ↔ protobuf messages
- Handles gRPC errors and retries
"""

import logging

import grpc
from planning.application.ports.context_port import ContextPort, ContextResponse

# Import protobuf stubs (generated during container build or via make generate-grpc)
# Planning Service will generate these from specs/fleet/context/v1/context.proto
from planning.gen import context_pb2_grpc
from planning.infrastructure.mappers.context_grpc_mapper import ContextGrpcMapper

logger = logging.getLogger(__name__)


class ContextServiceError(Exception):
    """Raised when Context Service gRPC call fails."""

    pass


class ContextServiceAdapter(ContextPort):
    """gRPC adapter for Context Service.

    Following Hexagonal Architecture:
    - Infrastructure layer (adapter)
    - Implements ContextPort (application layer interface)
    - Converts strings to protobuf and vice versa via mapper
    - Handles gRPC communication details

    Responsibilities:
    - Call Context Service GetContext gRPC endpoint
    - Convert string story_id → protobuf request (via mapper)
    - Convert protobuf response → ContextResponse (via mapper)
    - Handle gRPC errors and retries
    - Fail-fast initialization (channel/stub created in __init__)
    """

    def __init__(self, grpc_address: str, *, timeout_seconds: float = 5.0):
        """Initialize adapter with Context Service gRPC address.

        Fail-fast initialization: channel and stub are created immediately.
        If initialization fails, the adapter cannot be used.

        Args:
            grpc_address: Context Service gRPC address (e.g., "context-service:50054")
            timeout_seconds: Request timeout in seconds (default: 5.0)

        Raises:
            ValueError: If grpc_address is empty
            RuntimeError: If channel or stub creation fails
        """
        if not grpc_address or not grpc_address.strip():
            raise ValueError("grpc_address cannot be empty")

        self._address = grpc_address.strip()
        self._timeout = timeout_seconds

        # Fail-fast: initialize channel and stub immediately
        try:
            # Use insecure channel (can be upgraded to secure_channel if TLS required)
            self._channel = grpc.aio.insecure_channel(self._address)
            self._stub = context_pb2_grpc.ContextServiceStub(self._channel)
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize gRPC channel/stub for Context Service: {e}"
            ) from e

        logger.info(f"ContextServiceAdapter initialized: {self._address}")

    async def get_context(
        self,
        story_id: str,
        role: str,
        phase: str,
        token_budget: int = 2000,
    ) -> ContextResponse:
        """Get rehydrated context from Context Service.

        Implements ContextPort interface.

        Args:
            story_id: Story identifier (string)
            role: Role name (e.g., "ARCHITECT", "QA", "DEVOPS")
            phase: Work phase (e.g., "PLAN", "BUILD", "TEST")
            token_budget: Token budget hint (default: 2000, currently not used by service)

        Returns:
            ContextResponse with formatted context and metadata

        Raises:
            ContextServiceError: If gRPC call fails
        """
        try:
            logger.debug(
                f"Calling Context Service GetContext: story_id={story_id}, "
                f"role={role}, phase={phase}, token_budget={token_budget}"
            )

            # Map string story_id to proto request using mapper
            request = ContextGrpcMapper.to_get_context_request_from_string(
                story_id=story_id,
                role=role,
                phase=phase,
            )

            # Call GetContext RPC
            response = await self._stub.GetContext(request, timeout=self._timeout)

            # Extract context string from response using mapper
            context_str = ContextGrpcMapper.context_from_response(response)

            # Build ContextResponse (convert scopes list to tuple for immutability)
            scopes_tuple = tuple(response.scopes) if response.scopes else ()

            context_response = ContextResponse(
                context=context_str,
                token_count=response.token_count,
                scopes=scopes_tuple,
                version=response.version or "",
            )

            logger.info(
                f"Successfully fetched context for story {story_id} "
                f"({response.token_count} tokens, {len(scopes_tuple)} scopes)"
            )

            return context_response

        except grpc.RpcError as e:
            error_msg = (
                f"gRPC error calling Context Service: {e.code()} - {e.details()}. "
                f"story_id={story_id}, role={role}"
            )
            logger.error(error_msg)
            raise ContextServiceError(error_msg) from e

        except Exception as e:
            error_msg = (
                f"Unexpected error calling Context Service: {e}. story_id={story_id}"
            )
            logger.error(error_msg, exc_info=True)
            raise ContextServiceError(error_msg) from e

    async def close(self) -> None:
        """Close gRPC channel.

        Cleanup method to release resources.
        Fail-fast: channel must exist (initialized in __init__).
        """
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None
            logger.info("ContextServiceAdapter channel closed")

