"""Middleware for idempotent gRPC handlers.

Wraps gRPC handlers to provide idempotency via command log.
If request_id is present and response exists in command log, returns cached response.
Otherwise, executes handler and stores response.

Following Hexagonal Architecture:
- Infrastructure layer (gRPC-specific)
- Uses CommandLogPort (application port)
- No business logic, only orchestration
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from planning.application.ports.command_log_port import CommandLogPort

import grpc

logger = logging.getLogger(__name__)

# Type variables for request and response
RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")


def _create_error_response(
    response_type: type[ResponseT],
    error_msg: str,
) -> ResponseT:
    """Create error response with error message.

    Args:
        response_type: Protobuf response message type
        error_msg: Error message to set

    Returns:
        Error response instance
    """
    error_response = response_type()
    if hasattr(error_response, "success"):
        error_response.success = False
    if hasattr(error_response, "message"):
        error_response.message = error_msg
    return error_response


def _validate_and_extract_request_id(
    request: Any,
    handler_name: str,
    context: Any,
    response_type: type[ResponseT],
) -> str | ResponseT:
    """Validate request_id and extract it, returning error response if invalid.

    Args:
        request: gRPC request message
        handler_name: Handler function name (for logging)
        context: gRPC context
        response_type: Protobuf response message type

    Returns:
        request_id string if valid, error response if invalid
    """
    if not hasattr(request, "request_id"):
        error_msg = "request_id field is required for idempotent command execution"
        logger.error(f"{handler_name}: {error_msg}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details(error_msg)
        return _create_error_response(response_type, error_msg)

    request_id_value = request.request_id
    if not request_id_value:
        error_msg = "request_id cannot be empty"
        logger.error(f"{handler_name}: {error_msg}")
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details(error_msg)
        return _create_error_response(response_type, error_msg)

    return request_id_value.strip() if isinstance(request_id_value, str) else str(request_id_value)


async def _get_cached_response(
    command_log: CommandLogPort,
    request_id: str,
    response_type: type[ResponseT],
) -> ResponseT | None:
    """Get cached response from command log.

    Args:
        command_log: CommandLogPort implementation
        request_id: Request identifier
        response_type: Protobuf response message type

    Returns:
        Cached response if found, None otherwise
    """
    cached_response_bytes = await command_log.get_response(request_id)
    if cached_response_bytes is None:
        return None

    logger.info(f"Idempotent response cache hit: request_id={request_id}")
    response = response_type()
    response.ParseFromString(cached_response_bytes)  # type: ignore[attr-defined]
    return response


async def _store_response_if_successful(
    command_log: CommandLogPort,
    request_id: str,
    response: ResponseT,
) -> None:
    """Store response in command log if it indicates success.

    Args:
        command_log: CommandLogPort implementation
        request_id: Request identifier
        response: Response to store
    """
    should_cache = True
    if hasattr(response, "success"):
        should_cache = response.success

    if not should_cache:
        return

    try:
        response_bytes = response.SerializeToString()  # type: ignore[attr-defined]
        await command_log.store_response(request_id, response_bytes)
        logger.info(f"Idempotent response stored: request_id={request_id}")
    except Exception as e:
        # Log but don't fail - caching is best effort
        logger.warning(f"Failed to store idempotent response for {request_id}: {e}")


def idempotent_grpc_handler(
    command_log: CommandLogPort,
    response_type: type[ResponseT],
) -> Callable[
    [Callable[[RequestT, Any, Any], Awaitable[ResponseT]]],
    Callable[[RequestT, Any, Any], Awaitable[ResponseT]],
]:
    """Decorator factory for idempotent gRPC handlers.

    Usage:
        ```python
        from planning.gen import planning_pb2

        @idempotent_grpc_handler(
            command_log=command_log_adapter,
            response_type=planning_pb2.CreateTaskResponse,
        )
        async def create_task_handler(request, context, use_case):
            # Handler logic
            return response
        ```

    Args:
        command_log: CommandLogPort implementation for caching responses
        response_type: Protobuf response message type (for deserialization)

    Returns:
        Decorator function that wraps handler with idempotency logic
    """
    def decorator(
        handler: Callable[[RequestT, Any, Any], Awaitable[ResponseT]],
    ) -> Callable[[RequestT, Any, Any], Awaitable[ResponseT]]:
        """Wrap handler with idempotency logic.

        Args:
            handler: Original gRPC handler function

        Returns:
            Wrapped handler with idempotency
        """
        async def wrapped_handler(
            request: RequestT,
            context: Any,
            *args: Any,
            **kwargs: Any,
        ) -> ResponseT:
            """Wrapped handler with idempotency.

            Flow:
            1. Extract request_id from request (if present)
            2. If request_id exists, check command log
            3. If cached response found, return it
            4. Otherwise, execute handler and store response

            Args:
                request: gRPC request message
                context: gRPC context
                *args: Additional positional arguments
                **kwargs: Additional keyword arguments

            Returns:
                gRPC response message
            """
            # Validate and extract request_id
            request_id_or_error = _validate_and_extract_request_id(
                request,
                handler.__name__,
                context,
                response_type,
            )
            if isinstance(request_id_or_error, response_type):
                return request_id_or_error
            request_id = request_id_or_error

            try:
                # Check for cached response
                cached_response = await _get_cached_response(
                    command_log,
                    request_id,
                    response_type,
                )
                if cached_response is not None:
                    return cached_response

                # Execute handler
                logger.debug(f"Idempotent response cache miss: request_id={request_id}, executing handler")
                response = await handler(request, context, *args, **kwargs)

                # Store response if successful
                await _store_response_if_successful(command_log, request_id, response)

                return response

            except Exception as e:
                # If idempotency check fails, execute handler anyway (fail-open)
                logger.warning(f"Idempotency check failed for {request_id}: {e}, executing handler")
                return await handler(request, context, *args, **kwargs)

        return wrapped_handler

    return decorator
