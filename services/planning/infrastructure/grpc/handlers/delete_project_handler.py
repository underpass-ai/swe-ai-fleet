"""DeleteProject gRPC handler."""

import logging

from planning.application.usecases.delete_project_usecase import DeleteProjectUseCase
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.gen import planning_pb2

import grpc

logger = logging.getLogger(__name__)


async def delete_project_handler(
    request: planning_pb2.DeleteProjectRequest,
    context,
    use_case: DeleteProjectUseCase,
) -> planning_pb2.DeleteProjectResponse:
    """Handle DeleteProject RPC."""
    try:
        logger.info(f"DeleteProject: project_id={request.project_id}")

        if not request.project_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return planning_pb2.DeleteProjectResponse(
                success=False,
                message="project_id is required",
            )

        project_id = ProjectId(request.project_id)
        await use_case.execute(project_id)

        return planning_pb2.DeleteProjectResponse(
            success=True,
            message=f"Project deleted: {project_id.value}",
        )

    except ValueError as e:
        logger.warning(f"DeleteProject validation error: {e}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return planning_pb2.DeleteProjectResponse(success=False, message=str(e))

    except Exception as e:
        logger.error(f"DeleteProject error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return planning_pb2.DeleteProjectResponse(
            success=False,
            message=f"Internal error: {e}",
        )
