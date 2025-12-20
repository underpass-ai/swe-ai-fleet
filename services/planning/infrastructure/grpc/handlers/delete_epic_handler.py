"""DeleteEpic gRPC handler."""

import logging

from planning.application.usecases.delete_epic_usecase import DeleteEpicUseCase
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.gen import planning_pb2

import grpc

logger = logging.getLogger(__name__)


async def delete_epic_handler(
    request: planning_pb2.DeleteEpicRequest,
    context,
    use_case: DeleteEpicUseCase,
) -> planning_pb2.DeleteEpicResponse:
    """Handle DeleteEpic RPC."""
    try:
        logger.info(f"DeleteEpic: epic_id={request.epic_id}")

        if not request.epic_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return planning_pb2.DeleteEpicResponse(
                success=False,
                message="epic_id is required",
            )

        epic_id = EpicId(request.epic_id)
        await use_case.execute(epic_id)

        return planning_pb2.DeleteEpicResponse(
            success=True,
            message=f"Epic deleted: {epic_id.value}",
        )

    except ValueError as e:
        logger.warning(f"DeleteEpic validation error: {e}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return planning_pb2.DeleteEpicResponse(success=False, message=str(e))

    except Exception as e:
        logger.error(f"DeleteEpic error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return planning_pb2.DeleteEpicResponse(
            success=False,
            message=f"Internal error: {e}",
        )
