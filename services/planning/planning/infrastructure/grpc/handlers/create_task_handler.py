"""CreateTask gRPC handler."""

import logging
from uuid import uuid4

import grpc

from planning.application.usecases.create_task_usecase import CreateTaskUseCase
from planning.domain.value_objects.actors.role import Role, RoleType
from planning.domain.value_objects.content.task_description import TaskDescription
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.requests.create_task_request import CreateTaskRequest
from planning.domain.value_objects.statuses.task_type import TaskType
from planning.domain.value_objects.task_attributes.duration import Duration
from planning.domain.value_objects.task_attributes.priority import Priority
from planning.gen import planning_pb2
from planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper

logger = logging.getLogger(__name__)


async def create_task_handler(
    request: planning_pb2.CreateTaskRequest,
    context,
    use_case: CreateTaskUseCase,
) -> planning_pb2.CreateTaskResponse:
    """Handle CreateTask RPC."""
    try:
        logger.info(f"CreateTask: story_id={request.story_id}, plan_id={request.plan_id}")

        # Convert protobuf primitives → Value Objects (anti-corruption layer)
        story_id = StoryId(request.story_id)
        plan_id = PlanId(request.plan_id)
        task_type = TaskType(request.type) if request.type else TaskType.DEVELOPMENT

        # Generate task ID (auto-generation for gRPC requests)
        task_id = TaskId(f"T-{uuid4()}")

        # Handle description: TaskDescription cannot be empty, use title as fallback
        description_str = request.description.strip() if request.description else request.title
        title_vo = Title(request.title)
        description_vo = TaskDescription(description_str)

        # Default role: DEVELOPER (can be extended later)
        assigned_role = Role(RoleType.DEVELOPER)

        # Initialize Duration and Priority VOs explicitly (Fail Fast)
        # Pass values directly to VOs - they will validate and fail fast if invalid
        # Handler only converts protobuf → VOs, no business logic
        estimated_hours_vo = Duration(request.estimated_hours)
        # Priority: Use request value or default to 1 if not provided
        # For task derivation, priority is calculated dynamically from order (NOT hardcoded)
        # For manual creation via gRPC, priority comes from request or defaults to 1
        priority_vo = Priority.from_optional(request.priority)

        create_request = CreateTaskRequest(
            plan_id=plan_id,
            story_id=story_id,
            task_id=task_id,
            title=title_vo,
            description=description_vo,
            task_type=task_type,
            assigned_to=assigned_role,
            estimated_hours=estimated_hours_vo,
            priority=priority_vo,
        )

        # Execute use case with VO request
        task = await use_case.execute(create_request)

        return ResponseMapper.create_task_response(
            success=True,
            message=f"Task created: {task.task_id.value}",
            task=task,
        )

    except ValueError as e:
        logger.warning(f"CreateTask validation error: {e}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return ResponseMapper.create_task_response(success=False, message=str(e))

    except Exception as e:
        logger.error(f"CreateTask error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseMapper.create_task_response(success=False, message=f"Internal error: {e}")


async def create_task(
    request: planning_pb2.CreateTaskRequest,
    context,
    use_case: CreateTaskUseCase,
) -> planning_pb2.CreateTaskResponse:
    """Backward-compatibility shim."""
    return await create_task_handler(request, context, use_case)

