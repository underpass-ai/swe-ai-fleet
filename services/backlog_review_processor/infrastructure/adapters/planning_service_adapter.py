"""Planning Service gRPC adapter for Backlog Review Processor Service.

Following Hexagonal Architecture:
- Implements PlanningPort (application layer interface)
- Lives in infrastructure layer
- Handles gRPC communication with Planning Service
"""

import logging

import grpc
from backlog_review_processor.application.ports.planning_port import (
    AddAgentDeliberationRequest,
    PlanningPort,
    PlanningServiceError,
    TaskCreationRequest,
)

# Import protobuf stubs (generated during container build)
# Backlog Review Processor Service will generate these from specs/fleet/planning/v2/planning.proto
try:
    from backlog_review_processor.gen import planning_pb2, planning_pb2_grpc
except ImportError:
    # Fallback for development (protobuf stubs not generated yet)
    planning_pb2 = None
    planning_pb2_grpc = None

logger = logging.getLogger(__name__)


class PlanningServiceAdapter(PlanningPort):
    """gRPC adapter for Planning Service communication.

    Adapter responsibilities:
    - Connect to Planning Service via gRPC
    - Implement PlanningPort interface
    - Map domain VOs to protobuf messages
    - Map protobuf responses to domain VOs
    - Handle gRPC errors

    Following Hexagonal Architecture:
    - Implements port (interface) from application layer
    - Uses gRPC client (infrastructure detail)
    - Fail-fast on configuration errors
    """

    def __init__(
        self,
        grpc_address: str,
        timeout_seconds: float = 30.0,
    ):
        """Initialize adapter with gRPC configuration.

        Args:
            grpc_address: Planning Service address (e.g., "planning:50054")
            timeout_seconds: gRPC call timeout

        Raises:
            ValueError: If grpc_address is invalid
            RuntimeError: If protobuf stubs are not available
        """
        if not grpc_address or not grpc_address.strip():
            raise ValueError("grpc_address cannot be empty")

        if planning_pb2 is None or planning_pb2_grpc is None:
            raise RuntimeError(
                "Planning Service protobuf stubs not available. "
                "Generate protobuf stubs before instantiating PlanningServiceAdapter."
            )

        self.address = grpc_address
        self.timeout = timeout_seconds
        self.channel = grpc.aio.insecure_channel(grpc_address)
        self.stub = planning_pb2_grpc.PlanningServiceStub(self.channel)

        logger.info(f"PlanningServiceAdapter initialized: {grpc_address}")

    async def create_task(self, request: TaskCreationRequest) -> str:
        """Create a task in Planning Service.

        Args:
            request: Task creation request with all required fields

        Returns:
            Task ID of the created task

        Raises:
            PlanningServiceError: If creation fails
        """
        try:
            # Build protobuf request
            proto_request = planning_pb2.CreateTaskRequest(
                story_id=request.story_id.value,
                plan_id="",  # Tasks from backlog review don't have plan yet
                title=request.title,
                description=request.description,
                type="backlog_review_identified",  # Use lowercase enum value
                assigned_to="",  # Will be assigned later
                estimated_hours=request.estimated_hours,
                priority=1,  # Default priority, will be adjusted later
            )

            logger.info(
                f"📤 Creating task in Planning Service: "
                f"story={request.story_id.value}, title={request.title}"
            )

            # Execute gRPC call
            response = await self.stub.CreateTask(
                proto_request, timeout=self.timeout
            )

            if not response.success:
                error_msg = f"Planning Service returned error: {response.message}"
                logger.error(error_msg)
                raise PlanningServiceError(error_msg)

            task_id = response.task.task_id
            logger.info(
                f"✅ Task created in Planning Service: {task_id} "
                f"(story: {request.story_id.value})"
            )

            # Store deliberation relationship (this would be done via a separate call
            # or by extending the CreateTaskRequest to include deliberation metadata)
            # For now, we'll log it - the relationship can be stored later via
            # a separate Planning Service method or via Context Service

            return task_id

        except grpc.RpcError as e:
            error_msg = f"gRPC error calling Planning Service: {e.code()} - {e.details()}"
            logger.error(error_msg)
            raise PlanningServiceError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error calling Planning Service: {e}"
            logger.error(error_msg, exc_info=True)
            raise PlanningServiceError(error_msg) from e

    async def add_agent_deliberation(self, request: AddAgentDeliberationRequest) -> None:
        """Add an agent deliberation to Planning Service.

        Args:
            request: Add agent deliberation request with all required fields

        Raises:
            PlanningServiceError: If adding deliberation fails
        """
        try:
            # Serialize proposal to JSON string if dict
            import json

            if isinstance(request.proposal, dict):
                proposal_str = json.dumps(request.proposal)
            else:
                proposal_str = str(request.proposal)

            # Build protobuf request
            proto_request = planning_pb2.AddAgentDeliberationRequest(
                ceremony_id=request.ceremony_id.value,
                story_id=request.story_id.value,
                role=request.role,
                agent_id=request.agent_id,
                feedback=request.feedback,
                proposal=proposal_str,
                reviewed_at=request.reviewed_at,
            )

            logger.info(
                f"📤 Adding agent deliberation to Planning Service: "
                f"ceremony={request.ceremony_id.value}, "
                f"story={request.story_id.value}, "
                f"role={request.role}, "
                f"agent={request.agent_id}"
            )

            # Execute gRPC call
            response = await self.stub.AddAgentDeliberation(
                proto_request, timeout=self.timeout
            )

            if not response.success:
                error_msg = f"Planning Service returned error: {response.message}"
                logger.error(error_msg)
                raise PlanningServiceError(error_msg)

            logger.info(
                f"✅ Agent deliberation added to Planning Service: "
                f"ceremony={request.ceremony_id.value}, "
                f"story={request.story_id.value}, "
                f"role={request.role}"
            )

        except grpc.RpcError as e:
            error_msg = f"gRPC error calling Planning Service: {e.code()} - {e.details()}"
            logger.error(error_msg)
            raise PlanningServiceError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error calling Planning Service: {e}"
            logger.error(error_msg, exc_info=True)
            raise PlanningServiceError(error_msg) from e

    async def close(self) -> None:
        """Close gRPC channel.

        Cleanup method to release resources.
        """
        if self.channel:
            await self.channel.close()
            logger.info(f"Closed gRPC channel to Planning Service: {self.address}")

