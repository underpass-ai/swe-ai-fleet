"""Mapper between Context Service gRPC protos and domain value objects.

Following Hexagonal Architecture:
- Infrastructure layer mapper
- Converts domain VOs ↔ protobuf messages
- No business logic, pure data transformation
- Fail-fast validation
"""

from dataclasses import dataclass

from planning.domain.value_objects.identifiers.story_id import StoryId

# Import protobuf stubs (generated during container build or via make generate-grpc)
# Planning Service will generate these from specs/fleet/context/v1/context.proto
from planning.gen import context_pb2


@dataclass(frozen=True)
class ContextGrpcMapper:
    """Pure mapper for Context Service gRPC messages ↔ domain objects.

    This mapper handles conversions between:
    - Domain Value Objects (StoryId)
    - Protobuf messages (GetContextRequest, GetContextResponse)

    No I/O, no state mutation, no reflection. Just data transformation.

    Following DDD principles:
    - Domain VOs are immutable and validated
    - Conversion happens at infrastructure boundary
    - Fail-fast on invalid input
    """

    @staticmethod
    def to_get_context_request(
        story_id: StoryId,
        role: str,
        phase: str = "plan",
    ) -> context_pb2.GetContextRequest:
        """Convert domain objects to GetContextRequest proto.

        Args:
            story_id: Story identifier (domain VO)
            role: Role name (e.g., "developer", "architect")
            phase: Work phase (default: "plan")

        Returns:
            GetContextRequest protobuf message ready for gRPC call

        Raises:
            ValueError: If any input value is invalid
        """
        if not story_id or not story_id.value:
            raise ValueError("story_id cannot be empty")
        if not role or not role.strip():
            raise ValueError("role cannot be empty")
        if not phase or not phase.strip():
            raise ValueError("phase cannot be empty")

        # Convert phase to uppercase (proto expects uppercase: "PLAN", "BUILD", etc.)
        phase_upper = phase.upper()

        return context_pb2.GetContextRequest(
            story_id=story_id.value,
            role=role.strip(),
            phase=phase_upper,
        )

    @staticmethod
    def context_from_response(response: context_pb2.GetContextResponse) -> str:
        """Extract context string from GetContextResponse.

        Args:
            response: GetContextResponse protobuf message

        Returns:
            Formatted context string for LLM consumption

        Raises:
            ValueError: If response is invalid
        """
        if not response:
            raise ValueError("GetContextResponse cannot be None")

        context = response.context or ""
        # Return empty string if context is empty (not an error condition)
        return context

    @staticmethod
    def to_get_context_request_from_string(
        story_id: str,
        role: str,
        phase: str = "PLAN",
    ) -> context_pb2.GetContextRequest:
        """Convert string story_id to GetContextRequest proto.

        Args:
            story_id: Story identifier (string)
            role: Role name (e.g., "ARCHITECT", "QA")
            phase: Work phase (default: "PLAN")

        Returns:
            GetContextRequest protobuf message ready for gRPC call

        Raises:
            ValueError: If any input value is invalid
        """
        if not story_id or not story_id.strip():
            raise ValueError("story_id cannot be empty")
        if not role or not role.strip():
            raise ValueError("role cannot be empty")
        if not phase or not phase.strip():
            raise ValueError("phase cannot be empty")

        # Convert phase to uppercase (proto expects uppercase: "PLAN", "BUILD", etc.)
        phase_upper = phase.upper()

        return context_pb2.GetContextRequest(
            story_id=story_id.strip(),
            role=role.strip(),
            phase=phase_upper,
        )

