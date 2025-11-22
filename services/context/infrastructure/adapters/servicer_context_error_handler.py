"""Helper for handling servicer context errors.

Infrastructure layer helper that checks InternalServicerContext for errors
and raises appropriate exceptions.

Following Hexagonal Architecture:
- Infrastructure concern: error handling for gRPC servicer calls
- Separates error detection logic from handler orchestration
- Fail-fast error propagation
"""

import logging

from services.context.infrastructure.adapters.internal_servicer_context import (
    InternalServicerContext,
)

logger = logging.getLogger(__name__)


class ServicerContextErrorHandler:
    """Helper for checking and handling servicer context errors.

    Responsibility:
    - Check if InternalServicerContext has errors
    - Log errors with context
    - Raise RuntimeError with formatted error message
    - Fail-fast error propagation

    This is infrastructure-level error handling logic.
    Should NOT be in handlers or servicers.
    """

    @staticmethod
    def check_and_raise(
        context: InternalServicerContext,
        operation_name: str,
    ) -> None:
        """Check servicer context for errors and raise if found.

        Args:
            context: InternalServicerContext to check
            operation_name: Name of the operation (for error message)

        Raises:
            RuntimeError: If context has an error (fail-fast)
        """
        if context.has_error():
            error = context.get_error()
            error_msg = (
                f"{operation_name} failed: {error.code.name} - {error.details}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

