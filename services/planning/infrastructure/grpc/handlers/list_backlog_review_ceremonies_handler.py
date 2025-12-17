"""ListBacklogReviewCeremonies gRPC handler."""

import logging

import grpc

from planning.application.usecases.list_backlog_review_ceremonies_usecase import (
    ListBacklogReviewCeremoniesUseCase,
)
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)
from planning.gen import planning_pb2
from planning.infrastructure.mappers.response_protobuf_mapper import (
    ResponseProtobufMapper,
)

logger = logging.getLogger(__name__)


async def list_backlog_review_ceremonies_handler(
    request: planning_pb2.ListBacklogReviewCeremoniesRequest,
    context,
    use_case: ListBacklogReviewCeremoniesUseCase,
) -> planning_pb2.ListBacklogReviewCeremoniesResponse:
    """Handle ListBacklogReviewCeremonies RPC."""
    try:
        # Parse filters
        status_filter = None
        if request.status_filter:
            try:
                status_enum = BacklogReviewCeremonyStatusEnum(request.status_filter)
                status_filter = BacklogReviewCeremonyStatus(status_enum)
            except ValueError as e:
                logger.warning(f"Invalid status_filter: {request.status_filter}, error: {e}")
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                return ResponseProtobufMapper.list_backlog_review_ceremonies_response(
                    success=False,
                    message=f"Invalid status_filter: {request.status_filter}. "
                    f"Valid values: DRAFT, IN_PROGRESS, REVIEWING, COMPLETED, CANCELLED",
                    ceremonies=[],
                    total_count=0,
                )

        created_by = None
        if request.HasField("created_by"):
            try:
                # Validate even if empty string (UserName will raise ValueError)
                created_by = UserName(request.created_by)
            except ValueError as e:
                logger.warning(f"Invalid created_by: {request.created_by}, error: {e}")
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                return ResponseProtobufMapper.list_backlog_review_ceremonies_response(
                    success=False,
                    message=f"Invalid created_by: {e}",
                    ceremonies=[],
                    total_count=0,
                )

        # Parse pagination (defaults: limit=100, offset=0)
        limit = request.limit if request.limit > 0 else 100
        offset = request.offset if request.offset >= 0 else 0

        logger.info(
            f"ListBacklogReviewCeremonies: "
            f"status_filter={status_filter.to_string() if status_filter else None}, "
            f"created_by={created_by.value if created_by else None}, "
            f"limit={limit}, offset={offset}"
        )

        # Execute use case
        ceremonies = await use_case.execute(
            status_filter=status_filter,
            created_by=created_by,
            limit=limit,
            offset=offset,
        )

        return ResponseProtobufMapper.list_backlog_review_ceremonies_response(
            success=True,
            message=f"Found {len(ceremonies)} ceremonies",
            ceremonies=ceremonies,
            total_count=len(ceremonies),
        )

    except ValueError as e:
        # Validation errors (invalid limit, offset, etc.)
        logger.warning(f"ListBacklogReviewCeremonies validation error: {e}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        return ResponseProtobufMapper.list_backlog_review_ceremonies_response(
            success=False,
            message=f"Validation error: {e}",
            ceremonies=[],
            total_count=0,
        )

    except Exception as e:
        logger.error(f"ListBacklogReviewCeremonies error: {e}", exc_info=True)
        context.set_code(grpc.StatusCode.INTERNAL)
        return ResponseProtobufMapper.list_backlog_review_ceremonies_response(
            success=False,
            message=f"Internal error: {e}",
            ceremonies=[],
            total_count=0,
        )
