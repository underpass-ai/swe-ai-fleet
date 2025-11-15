"""Context Service gRPC adapter for Planning Service.

Infrastructure Adapter (Hexagonal Architecture):
- Implements ContextPort interface
- Calls Context Service via gRPC
- Converts domain VOs ↔ protobuf messages
- Handles gRPC errors and retries
"""

import logging
from typing import Any

import grpc

from planning.application.ports.context_port import ContextPort
from planning.domain.value_objects.identifiers.story_id import StoryId

logger = logging.getLogger(__name__)


class ContextServiceError(Exception):
    """Raised when Context Service gRPC call fails."""

    pass


class ContextServiceAdapter(ContextPort):
    """gRPC adapter for Context Service.

    Following Hexagonal Architecture:
    - Infrastructure layer (adapter)
    - Implements ContextPort (application layer interface)
    - Converts domain VOs to protobuf and vice versa
    - Handles gRPC communication details

    Responsibilities:
    - Call Context Service GetContext gRPC endpoint
    - Convert StoryId VO → protobuf string
    - Return context string from response
    - Handle gRPC errors and retries
    """

    def __init__(self, grpc_address: str):
        """Initialize adapter with Context Service gRPC address.

        Args:
            grpc_address: Context Service gRPC address (e.g., "localhost:50054")
        """
        self.grpc_address = grpc_address
        # TODO: Import and initialize gRPC stub when protobuf files are available
        # For now, this is a placeholder structure
        self._stub = None  # Will be initialized with actual gRPC stub

        logger.info(f"ContextServiceAdapter initialized: {grpc_address}")

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
                f"Calling Context Service GetContext: story_id={story_id}, "
                f"role={role}, phase={phase}"
            )

            # TODO: Implement actual gRPC call when protobuf files are available
            # Example structure:
            # request = context_pb2.GetContextRequest(
            #     story_id=story_id.value,  # VO → string at boundary
            #     role=role,
            #     phase=phase,
            # )
            # response = await self._stub.GetContext(request)
            # return response.context

            # Placeholder: raise NotImplementedError until protobuf is available
            raise NotImplementedError(
                "Context Service gRPC integration pending protobuf generation. "
                "Need to generate context_pb2 and context_pb2_grpc from .proto files."
            )

        except grpc.RpcError as e:
            error_msg = (
                f"gRPC error calling Context Service: {e.code()} - {e.details()}. "
                f"story_id={story_id}, role={role}"
            )
            logger.error(error_msg)
            raise ContextServiceError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error calling Context Service: {e}. story_id={story_id}"
            logger.error(error_msg, exc_info=True)
            raise ContextServiceError(error_msg) from e

