"""gRPC adapter for Orchestrator Service."""

import grpc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fleet.orchestrator.v1 import orchestrator_pb2, orchestrator_pb2_grpc


class GrpcOrchestratorAdapter:
    """Adapter for Orchestrator Service gRPC calls."""

    def __init__(self, service_url: str) -> None:
        """Initialize adapter.
        
        Args:
            service_url: gRPC service URL (e.g., "localhost:50055")
        """
        if not service_url:
            raise ValueError("service_url cannot be empty")
        self._service_url = service_url
        self._channel: grpc.aio.Channel | None = None
        self._stub: "orchestrator_pb2_grpc.OrchestratorServiceStub | None" = None

    async def connect(self) -> None:
        """Establish gRPC connection."""
        from fleet.orchestrator.v1 import orchestrator_pb2_grpc
        
        self._channel = grpc.aio.insecure_channel(self._service_url)
        self._stub = orchestrator_pb2_grpc.OrchestratorServiceStub(self._channel)

    async def close(self) -> None:
        """Close gRPC connection."""
        if self._channel:
            await self._channel.close()

    async def create_council(
        self,
        role: str,
        num_agents: int,
        agent_type: str,
        model_profile: str
    ) -> tuple[str, int, list[str]]:
        """Create a council for a specific role."""
        if not self._stub:
            raise RuntimeError("Adapter not connected. Call connect() first.")

        from fleet.orchestrator.v1 import orchestrator_pb2

        config = orchestrator_pb2.CouncilConfig(
            agent_type=agent_type,
            model_profile=model_profile
        )

        request = orchestrator_pb2.CreateCouncilRequest(
            role=role,
            num_agents=num_agents,
            config=config
        )

        try:
            response = await self._stub.CreateCouncil(request)
            return (
                response.council_id,
                response.agents_created,
                list(response.agent_ids)
            )
        except grpc.RpcError as e:
            raise RuntimeError(f"gRPC call failed: {e.code()} - {e.details()}") from e

    async def deliberate(
        self,
        task_description: str,
        role: str,
        rounds: int,
        num_agents: int,
        constraints: dict[str, str]
    ) -> tuple[list[dict], str, int]:
        """Execute peer deliberation on a task."""
        if not self._stub:
            raise RuntimeError("Adapter not connected. Call connect() first.")

        from fleet.orchestrator.v1 import orchestrator_pb2

        task_constraints = orchestrator_pb2.TaskConstraints(
            rubric=constraints.get("rubric", ""),
            requirements=constraints.get("requirements", "").split(",") if constraints.get("requirements") else []
        )

        request = orchestrator_pb2.DeliberateRequest(
            task_description=task_description,
            role=role,
            constraints=task_constraints,
            rounds=rounds,
            num_agents=num_agents
        )

        try:
            response = await self._stub.Deliberate(request)
            
            # Convert protobuf results to dict
            results = []
            for result in response.results:
                results.append({
                    "author_id": result.proposal.author_id,
                    "author_role": result.proposal.author_role,
                    "content": result.proposal.content,
                    "score": result.score,
                    "rank": result.rank
                })
            
            return (results, response.winner_id, response.duration_ms)
        except grpc.RpcError as e:
            raise RuntimeError(f"gRPC call failed: {e.code()} - {e.details()}") from e

    async def delete_council(self, role: str) -> tuple[bool, int]:
        """Delete a council and its agents."""
        if not self._stub:
            raise RuntimeError("Adapter not connected. Call connect() first.")

        from fleet.orchestrator.v1 import orchestrator_pb2

        request = orchestrator_pb2.DeleteCouncilRequest(role=role)

        try:
            response = await self._stub.DeleteCouncil(request)
            return (response.success, response.agents_removed)
        except grpc.RpcError as e:
            raise RuntimeError(f"gRPC call failed: {e.code()} - {e.details()}") from e

