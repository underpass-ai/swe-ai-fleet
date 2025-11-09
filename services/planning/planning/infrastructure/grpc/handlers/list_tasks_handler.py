"""ListTasks gRPC handler."""

import logging

import grpc

from planning.application.usecases.list_tasks_usecase import ListTasksUseCase
from planning.domain.value_objects.plan_id import PlanId
from planning.domain.value_objects.story_id import StoryId
from planning.gen import planning_pb2
from planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper

logger = logging.getLogger(__name__)


async def list_tasks(
    request: planning_pb2.ListTasksRequest,
    context,
    use_case: ListTasksUseCase,
) -> planning_pb2.ListTasksResponse:
    """Handle ListTasks RPC."""
    try:
        story_id = StoryId(request.story_id) if request.story_id else None
        limit = request.limit if request.limit > 0 else 100
        offset = request.offset if request.offset >= 0 else 0

        logger.info(f"ListTasks: story_id={story_id}, limit={limit}")

        tasks = await use_case.execute(
            story_id=story_id,
            plan_id=None,  # Not in protobuf spec
            limit=limit,
            offset=offset,
        )

        return ResponseMapper.list_tasks_response(
            success=True,
            message=f"Found {len(tasks)} tasks",
            tasks=tasks,
        )

    except Exception as e:
        logger.error(f"ListTasks error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseMapper.list_tasks_response(
            success=False,
            message=f"Error: {e}",
            tasks=[],
        )

