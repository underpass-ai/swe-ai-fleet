"""ListProjects gRPC handler."""

import logging

import grpc

from planning.application.usecases.list_projects_usecase import ListProjectsUseCase
from planning.gen import planning_pb2
from planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper

logger = logging.getLogger(__name__)


async def list_projects(
    request: planning_pb2.ListProjectsRequest,
    context,
    use_case: ListProjectsUseCase,
) -> planning_pb2.ListProjectsResponse:
    """Handle ListProjects RPC."""
    try:
        limit = request.limit if request.limit > 0 else 100
        offset = request.offset if request.offset >= 0 else 0

        logger.info(f"ListProjects: limit={limit}, offset={offset}")

        projects = await use_case.execute(limit=limit, offset=offset)

        return ResponseMapper.list_projects_response(
            success=True,
            message=f"Found {len(projects)} projects",
            projects=projects,
        )

    except Exception as e:
        logger.error(f"ListProjects error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseMapper.list_projects_response(
            success=False,
            message=f"Error: {e}",
            projects=[],
        )

