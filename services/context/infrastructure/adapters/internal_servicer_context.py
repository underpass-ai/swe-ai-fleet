"""Internal servicer context adapter for non-gRPC calls.

Infrastructure layer adapter that implements gRPC ServicerContext interface
for internal calls (not through actual gRPC network).

Following Hexagonal Architecture:
- Adapter pattern: adapts gRPC servicer interface for internal use
- Infrastructure concern: bridges NATS handler to gRPC servicer methods
"""

import grpc
from services.context.infrastructure.adapters.servicer_error import ServicerError


class InternalServicerContext:
    """Minimal servicer context adapter for internal calls (not through gRPC).

    This adapter implements the gRPC ServicerContext interface to allow
    NATS handlers to call servicer methods directly without going through
    the gRPC network layer.

    Responsibilities:
    - Captures error information set by servicer methods
    - Provides error detection for callers (NATS handler)
    - Uses explicit error value object instead of None sentinels

    Following Hexagonal Architecture:
    - Infrastructure adapter (implements external protocol interface)
    - No domain logic (pure infrastructure concern)
    """

    def __init__(self) -> None:
        """Initialize context with no error state."""
        self._has_error: bool = False
        self._error_code: grpc.StatusCode = grpc.StatusCode.OK
        self._error_details: str = ""

    def set_code(self, code: grpc.StatusCode) -> None:
        """Set gRPC status code (captured for error detection)."""
        self._has_error = True
        self._error_code = code

    def set_details(self, details: str) -> None:
        """Set gRPC error details (captured for error detection)."""
        self._error_details = details

    def has_error(self) -> bool:
        """Check if an error was set on this context."""
        return self._has_error

    def get_error(self) -> ServicerError:
        """Get error information as value object.

        Returns:
            ServicerError value object

        Raises:
            RuntimeError: If no error was set (fail-fast)
        """
        if not self._has_error:
            raise RuntimeError("No error set on context - call has_error() first")
        return ServicerError(code=self._error_code, details=self._error_details)

