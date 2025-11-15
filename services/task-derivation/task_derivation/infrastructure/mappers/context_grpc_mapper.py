"""Mapper between Context Service gRPC protos and domain value objects."""

from __future__ import annotations

from dataclasses import dataclass

from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.domain.value_objects.task_derivation.context.derivation_phase import (
    DerivationPhase,
)

# Import context proto stubs (generated during build)
try:
    from task_derivation.gen import context_pb2
except ImportError:
    # Fallback: context_pb2 will be loaded at runtime when needed
    context_pb2 = None  # type: ignore


@dataclass(frozen=True)
class ContextGrpcMapper:
    """Pure mapper for Context Service gRPC messages ↔ domain objects.
    
    This mapper handles conversions between:
    - Domain Value Objects (StoryId, ContextRole, DerivationPhase)
    - Protobuf messages (GetContextRequest)
    
    No I/O, no state mutation, no reflection. Just data transformation.
    """

    @staticmethod
    def to_get_context_request(
        story_id: StoryId,
        role: ContextRole,
        phase: DerivationPhase,
    ) -> context_pb2.GetContextRequest:
        """Convert domain objects to GetContextRequest proto.
        
        Args:
            story_id: Story identifier
            role: Context role (e.g., "developer", "qa")
            phase: Derivation phase (e.g., "PLAN", "BUILD", "TEST")
        
        Returns:
            GetContextRequest protobuf message ready for gRPC call
        
        Raises:
            ValueError: If any input value object is invalid
        """
        if not story_id or not story_id.value:
            raise ValueError("story_id cannot be empty")
        if not role or not role.value:
            raise ValueError("role cannot be empty")
        if not phase or not phase.value:
            raise ValueError("phase cannot be empty")

        # Convert phase enum to proto field name (PLAN -> "PLAN", etc.)
        phase_str = phase.value.upper()

        return context_pb2.GetContextRequest(
            story_id=story_id.value,
            role=role.value,
            phase=phase_str,
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
        if not context:
            # Return empty string rather than raising - context might be empty
            # but not an error condition
            return ""

        return context

