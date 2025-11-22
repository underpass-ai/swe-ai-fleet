"""Servicer error value object for internal gRPC context.

Infrastructure layer value object representing gRPC error state.
Following Hexagonal Architecture: infrastructure concern (gRPC protocol).
"""

from dataclasses import dataclass

import grpc


@dataclass(frozen=True)
class ServicerError:
    """Error information captured from servicer method.

    Immutable value object representing an error state.
    This is an infrastructure concern (gRPC protocol), not domain logic.
    """

    code: grpc.StatusCode
    details: str

    def __post_init__(self) -> None:
        """Validate error (fail-fast)."""
        if not self.details or not self.details.strip():
            raise ValueError("Error details cannot be empty")

