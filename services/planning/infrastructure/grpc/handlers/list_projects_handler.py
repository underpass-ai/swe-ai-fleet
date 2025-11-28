"""ListProjects gRPC handler."""

import logging

from planning.application.usecases.list_projects_usecase import ListProjectsUseCase
from planning.domain.value_objects.statuses.project_status import ProjectStatus
from planning.gen import planning_pb2
from planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper

import grpc

logger = logging.getLogger(__name__)


async def list_projects_handler(
    request: planning_pb2.ListProjectsRequest,
    context,
    use_case: ListProjectsUseCase,
) -> planning_pb2.ListProjectsResponse:
    """Handle ListProjects RPC."""
    try:
        limit = request.limit if request.limit > 0 else 100
        offset = request.offset if request.offset >= 0 else 0

        # Parse status filter if provided
        status_filter: ProjectStatus | None = None
        if request.status_filter:
            try:
                status_filter = ProjectStatus(request.status_filter)
            except ValueError:
                logger.warning(f"Invalid status_filter: {request.status_filter}")
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                return ResponseMapper.list_projects_response(
                    success=False,
                    message=f"Invalid status_filter: {request.status_filter}",
                    projects=[],
                )

        logger.info(
            f"ListProjects: status_filter={status_filter}, limit={limit}, offset={offset}"
        )

        projects = await use_case.execute(
            status_filter=status_filter,
            limit=limit,
            offset=offset,
        )

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

