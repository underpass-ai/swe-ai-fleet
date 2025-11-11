"""CreateTask gRPC handler."""

import logging

import grpc

from planning.application.usecases.create_task_usecase import CreateTaskUseCase
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.task_type import TaskType
from planning.gen import planning_pb2
from planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper

logger = logging.getLogger(__name__)


async def create_task(
    request: planning_pb2.CreateTaskRequest,
    context,
    use_case: CreateTaskUseCase,
) -> planning_pb2.CreateTaskResponse:
    """Handle CreateTask RPC."""
    try:
        logger.info(f"CreateTask: story_id={request.story_id}, plan_id={request.plan_id}")

        story_id = StoryId(request.story_id)
        plan_id = PlanId(request.plan_id)
        task_type = TaskType(request.type) if request.type else TaskType.DEVELOPMENT

        task = await use_case.execute(
            story_id=story_id,
            plan_id=plan_id,
            title=request.title,
            description=request.description,
            type=task_type,
        )

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

