"""CreateProject gRPC handler."""

import logging

from planning.gen import planning_pb2

import grpc
from planning.application.usecases.create_project_usecase import CreateProjectUseCase
from planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper

logger = logging.getLogger(__name__)


async def create_project_handler(
    request: planning_pb2.CreateProjectRequest,
    context,
    use_case: CreateProjectUseCase,
) -> planning_pb2.CreateProjectResponse:
    """Handle CreateProject RPC."""
    try:
        logger.info(f"CreateProject: name={request.name}")

        project = await use_case.execute(
            name=request.name,
            description=request.description,
            owner=request.owner,
        )

        return ResponseMapper.create_project_response(
            success=True,
            message=f"Project created: {project.project_id.value}",
            project=project,
        )

    except ValueError as e:
        logger.warning(f"CreateProject validation error: {e}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return ResponseMapper.create_project_response(success=False, message=str(e))

    except Exception as e:
        logger.error(f"CreateProject error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseMapper.create_project_response(success=False, message=f"Internal error: {e}")


async def create_project(
    request: planning_pb2.CreateProjectRequest,
    context,
    use_case: CreateProjectUseCase,
) -> planning_pb2.CreateProjectResponse:
    """Backward-compatibility shim."""
    return await create_project_handler(request, context, use_case)

