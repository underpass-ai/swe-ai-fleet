"""GetTask gRPC handler."""

import logging

import grpc

from planning.application.usecases.get_task_usecase import GetTaskUseCase
from planning.domain.value_objects.task_id import TaskId
from planning.gen import planning_pb2
from planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper

logger = logging.getLogger(__name__)


async def get_task(
    request: planning_pb2.GetTaskRequest,
    context,
    use_case: GetTaskUseCase,
) -> planning_pb2.TaskResponse:
    """Handle GetTask RPC."""
    try:
        logger.info(f"GetTask: task_id={request.task_id}")

        task_id = TaskId(request.task_id)
        task = await use_case.execute(task_id)

        if not task:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return ResponseMapper.task_response()

        return ResponseMapper.task_response(task=task)

    except Exception as e:
        logger.error(f"GetTask error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseMapper.task_response()

