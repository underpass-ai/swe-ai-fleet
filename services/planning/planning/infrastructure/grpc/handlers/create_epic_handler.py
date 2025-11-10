"""CreateEpic gRPC handler."""

import logging

import grpc

from planning.application.usecases.create_epic_usecase import CreateEpicUseCase
from planning.domain.value_objects.project_id import ProjectId
from planning.gen import planning_pb2
from planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper

logger = logging.getLogger(__name__)


async def create_epic(
    request: planning_pb2.CreateEpicRequest,
    context,
    use_case: CreateEpicUseCase,
) -> planning_pb2.CreateEpicResponse:
    """Handle CreateEpic RPC."""
    try:
        logger.info(f"CreateEpic: project_id={request.project_id}, title={request.title}")

        project_id = ProjectId(request.project_id)
        epic = await use_case.execute(
            project_id=project_id,
            title=request.title,
            description=request.description,
        )

        return ResponseMapper.create_epic_response(
            success=True,
            message=f"Epic created: {epic.epic_id.value}",
            epic=epic,
        )

    except ValueError as e:
        logger.warning(f"CreateEpic validation error: {e}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return ResponseMapper.create_epic_response(success=False, message=str(e))

    except Exception as e:
        logger.error(f"CreateEpic error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseMapper.create_epic_response(success=False, message=f"Internal error: {e}")

