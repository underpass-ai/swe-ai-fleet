"""Context Service gRPC adapter for Planning Service.

Infrastructure Adapter (Hexagonal Architecture):
- Implements ContextPort interface
- Calls Context Service via gRPC
- Converts domain VOs ↔ protobuf messages
- Handles gRPC errors and retries
"""

import logging

import grpc

from planning.application.ports.context_port import ContextPort
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.infrastructure.mappers.context_grpc_mapper import ContextGrpcMapper

# Import protobuf stubs (generated during container build or via make generate-grpc)
# Planning Service will generate these from specs/fleet/context/v1/context.proto
from planning.gen import context_pb2_grpc

logger = logging.getLogger(__name__)


class ContextServiceError(Exception):
    """Raised when Context Service gRPC call fails."""

    pass


class ContextServiceAdapter(ContextPort):
    """gRPC adapter for Context Service.

    Following Hexagonal Architecture:
    - Infrastructure layer (adapter)
    - Implements ContextPort (application layer interface)
    - Converts domain VOs to protobuf and vice versa via mapper
    - Handles gRPC communication details

    Responsibilities:
    - Call Context Service GetContext gRPC endpoint
    - Convert StoryId VO → protobuf string (via mapper)
    - Return context string from response (via mapper)
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
        story_id: StoryId,
        role: str,
        phase: str = "plan",
    ) -> str:
        """Get rehydrated context from Context Service.

        Args:
            story_id: Story identifier (domain VO)
            role: Role name (e.g., "developer", "architect")
            phase: Work phase (default: "plan")

        Returns:
            Context string (formatted prompt blocks)

        Raises:
            ContextServiceError: If gRPC call fails
        """
        try:
            logger.debug(
                f"Calling Context Service GetContext: story_id={story_id.value}, "
                f"role={role}, phase={phase}"
            )

            # Map domain objects to proto request using mapper
            request = ContextGrpcMapper.to_get_context_request(
                story_id=story_id,
                role=role,
                phase=phase,
            )

            # Call GetContext RPC
            response = await self._stub.GetContext(request, timeout=self._timeout)

            # Extract context string from response using mapper
            context_str = ContextGrpcMapper.context_from_response(response)

            logger.info(
                f"Successfully fetched context for story {story_id.value} "
                f"({response.token_count} tokens)"
            )

            return context_str

        except grpc.RpcError as e:
            error_msg = (
                f"gRPC error calling Context Service: {e.code()} - {e.details()}. "
                f"story_id={story_id.value}, role={role}"
            )
            logger.error(error_msg)
            raise ContextServiceError(error_msg) from e

        except Exception as e:
            error_msg = (
                f"Unexpected error calling Context Service: {e}. story_id={story_id.value}"
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

