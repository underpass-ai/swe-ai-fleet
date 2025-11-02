"""gRPC adapter for Context Service."""

from typing import TYPE_CHECKING

import grpc

if TYPE_CHECKING:
    from fleet.context.v1 import context_pb2_grpc


class GrpcContextAdapter:
    """Adapter for Context Service gRPC calls."""

    def __init__(self, service_url: str) -> None:
        """Initialize adapter.

        Args:
            service_url: gRPC service URL (e.g., "localhost:50054")
        """
        if not service_url:
            raise ValueError("service_url cannot be empty")
        self._service_url = service_url
        self._channel: grpc.aio.Channel | None = None
        self._stub: context_pb2_grpc.ContextServiceStub | None = None

    async def connect(self) -> None:
        """Establish gRPC connection."""
        # Import here to avoid dependency issues in non-containerized environments
        from fleet.context.v1 import context_pb2_grpc

        self._channel = grpc.aio.insecure_channel(self._service_url)
        self._stub = context_pb2_grpc.ContextServiceStub(self._channel)

    async def close(self) -> None:
        """Close gRPC connection."""
        if self._channel:
            await self._channel.close()

    async def create_story(
        self,
        story_id: str,
        title: str,
        description: str,
        initial_phase: str
    ) -> tuple[str, str]:
        """Create a new user story in Neo4j and Valkey."""
        if not self._stub:
            raise RuntimeError("Adapter not connected. Call connect() first.")

        from fleet.context.v1 import context_pb2

        request = context_pb2.CreateStoryRequest(
            story_id=story_id,
            title=title,
            description=description,
            initial_phase=initial_phase
        )

        try:
            response = await self._stub.CreateStory(request)
            return (response.context_id, response.current_phase)
        except grpc.RpcError as e:
            raise RuntimeError(f"gRPC call failed: {e.code()} - {e.details()}") from e

    async def add_project_decision(
        self,
        story_id: str,
        decision_type: str,
        title: str,
        rationale: str,
        alternatives_considered: str,
        metadata: dict[str, str]
    ) -> str:
        """Add a project decision to Neo4j."""
        if not self._stub:
            raise RuntimeError("Adapter not connected. Call connect() first.")

        from fleet.context.v1 import context_pb2

        request = context_pb2.AddProjectDecisionRequest(
            story_id=story_id,
            decision_type=decision_type,
            title=title,
            rationale=rationale,
            alternatives_considered=alternatives_considered,
            metadata=metadata
        )

        try:
            response = await self._stub.AddProjectDecision(request)
            return response.decision_id
        except grpc.RpcError as e:
            raise RuntimeError(f"gRPC call failed: {e.code()} - {e.details()}") from e

    async def transition_phase(
        self,
        story_id: str,
        from_phase: str,
        to_phase: str,
        rationale: str
    ) -> tuple[str, str]:
        """Record a phase transition in Neo4j."""
        if not self._stub:
            raise RuntimeError("Adapter not connected. Call connect() first.")

        from fleet.context.v1 import context_pb2

        request = context_pb2.TransitionPhaseRequest(
            story_id=story_id,
            from_phase=from_phase,
            to_phase=to_phase,
            rationale=rationale
        )

        try:
            response = await self._stub.TransitionPhase(request)
            return (response.story_id, response.transitioned_at)
        except grpc.RpcError as e:
            raise RuntimeError(f"gRPC call failed: {e.code()} - {e.details()}") from e

