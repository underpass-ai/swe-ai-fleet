"""GetEpic gRPC handler."""

import logging

from planning.gen import planning_pb2

import grpc
from planning.application.usecases.get_epic_usecase import GetEpicUseCase
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper

logger = logging.getLogger(__name__)


async def get_epic_handler(
    request: planning_pb2.GetEpicRequest,
    context,
    use_case: GetEpicUseCase,
) -> planning_pb2.EpicResponse:
    """Handle GetEpic RPC."""
    try:
        logger.info(f"GetEpic: epic_id={request.epic_id}")

        epic_id = EpicId(request.epic_id)
        epic = await use_case.execute(epic_id)

        if not epic:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return ResponseMapper.epic_response()

        return ResponseMapper.epic_response(epic=epic)

    except Exception as e:
        logger.error(f"GetEpic error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseMapper.epic_response()


async def get_epic(
    request: planning_pb2.GetEpicRequest,
    context,
    use_case: GetEpicUseCase,
) -> planning_pb2.EpicResponse:
    """Backward-compatibility shim."""
    return await get_epic_handler(request, context, use_case)

