"""GetProject gRPC handler."""

import logging

from planning.gen import planning_pb2

import grpc
from planning.application.usecases.get_project_usecase import GetProjectUseCase
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper

logger = logging.getLogger(__name__)


async def get_project_handler(
    request: planning_pb2.GetProjectRequest,
    context,
    use_case: GetProjectUseCase,
) -> planning_pb2.ProjectResponse:
    """Handle GetProject RPC."""
    try:
        logger.info(f"GetProject: project_id={request.project_id}")

        project_id = ProjectId(request.project_id)
        project = await use_case.execute(project_id)

        if not project:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return planning_pb2.ProjectResponse()

        return ResponseMapper.project_response(
            success=True,
            message="Project found",
            project=project,
        )

    except Exception as e:
        logger.error(f"GetProject error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return planning_pb2.ProjectResponse()


async def get_project(
    request: planning_pb2.GetProjectRequest,
    context,
    use_case: GetProjectUseCase,
) -> planning_pb2.ProjectResponse:
    """Backward-compatibility shim."""
    return await get_project_handler(request, context, use_case)

