"""Mapper for Orchestrator Service gRPC requests.

Infrastructure Mapper:
- Converts domain DTOs ↔ protobuf messages
- Lives in infrastructure layer
- Handles external format conversions
- NO business logic - only translation

Following Hexagonal Architecture:
- Separates mapping concern from adapter
- Stateless (all static methods)
- Works with domain DTOs and protobuf
"""

from planning.application.ports.orchestrator_port import DeliberationRequest
from planning.gen import orchestrator_pb2


class OrchestratorProtobufMapper:
    """Mapper for Orchestrator protobuf messages.

    Following Hexagonal Architecture:
    - Lives in infrastructure layer
    - Converts domain DTOs to external format (protobuf)
    - NO business logic - only translation
    - Stateless (all static methods)
    """

    @staticmethod
    def to_deliberate_request(
        request: DeliberationRequest,
    ) -> orchestrator_pb2.DeliberateRequest:
        """Map domain DeliberationRequest DTO to protobuf message.

        Args:
            request: Domain DTO with deliberation parameters

        Returns:
            Protobuf DeliberateRequest message
        """
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

