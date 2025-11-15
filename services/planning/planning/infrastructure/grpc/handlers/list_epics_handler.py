"""ListEpics gRPC handler."""

import logging

import grpc

from planning.application.usecases.list_epics_usecase import ListEpicsUseCase
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.gen import planning_pb2
from planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper

logger = logging.getLogger(__name__)


async def list_epics_handler(
    request: planning_pb2.ListEpicsRequest,
    context,
    use_case: ListEpicsUseCase,
) -> planning_pb2.ListEpicsResponse:
    """Handle ListEpics RPC."""
    try:
        project_id = ProjectId(request.project_id) if request.project_id else None
        limit = request.limit if request.limit > 0 else 100
        offset = request.offset if request.offset >= 0 else 0

        logger.info(f"ListEpics: project_id={project_id}")

        epics = await use_case.execute(
            project_id=project_id,
            limit=limit,
            offset=offset,
        )

        return ResponseMapper.list_epics_response(
            success=True,
            message=f"Found {len(epics)} epics",
            epics=epics,
        )

    except Exception as e:
        logger.error(f"ListEpics error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseMapper.list_epics_response(
            success=False,
            message=f"Error: {e}",
            epics=[],
        )

