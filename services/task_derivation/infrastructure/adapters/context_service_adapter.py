"""gRPC adapter for Context Service, implementing ContextPort."""

from __future__ import annotations

import logging
from typing import Any

import grpc
from grpc import aio
from task_derivation.application.ports.context_port import ContextPort
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.domain.value_objects.task_derivation.context.derivation_phase import (
    DerivationPhase,
)
from task_derivation.gen import context_pb2_grpc
from task_derivation.infrastructure.mappers.context_grpc_mapper import (
    ContextGrpcMapper,
)

logger = logging.getLogger(__name__)


class ContextServiceAdapter(ContextPort):
    """Concrete adapter for fetching rehydrated story context via gRPC."""

    def __init__(
        self,
        address: str,
        *,
        timeout_seconds: float = 5.0,
    ) -> None:
        """Initialize adapter with Context Service address.

        Args:
            address: gRPC service address (e.g., "context-service:50054")
            timeout_seconds: Request timeout

        Raises:
            ValueError: If address is empty
        """
        if not address or not address.strip():
            raise ValueError("ContextServiceAdapter address cannot be empty")

        self._address = address
        self._timeout = timeout_seconds
        self._stub: Any = None
        self._channel: aio.Channel | None = None

    async def get_context(
        self,
        story_id: StoryId,
        role: ContextRole,
        phase: DerivationPhase = DerivationPhase.PLAN,
    ) -> str:
        """Fetch rehydrated context from Context Service.

        Args:
            story_id: Story identifier
            role: Context role (e.g., "developer", "qa")
            phase: Derivation phase (defaults to PLAN)

        Returns:
            Formatted context blocks as string

        Raises:
            grpc.RpcError: If service call fails
        """
        try:
            logger.info(
                "Fetching context for story %s, role %s, phase %s",
                story_id.value,
                role.value,
                phase.value,
            )

            # Lazy initialization: create channel on first use
            if self._channel is None:
                self._channel = aio.secure_channel(
                    self._address,
                    grpc.ssl_channel_credentials(),
                )

            # Create stub on first use
            if self._stub is None:
                self._stub = context_pb2_grpc.ContextServiceStub(self._channel)

            # Map domain objects to proto request using mapper
            request = ContextGrpcMapper.to_get_context_request(
                story_id=story_id,
                role=role,
                phase=phase,
            )

            # Call GetContext RPC
            response = await self._stub.GetContext(request, timeout=self._timeout)

            # Extract context string from response using mapper
            context_str = ContextGrpcMapper.context_from_response(response)

            logger.info(
                "Successfully fetched context for story %s (%d tokens)",
                story_id.value,
                response.token_count,
            )

            return context_str

        except Exception as exc:
            logger.error(
                "Failed to fetch context for story %s: %s",
                story_id.value,
                exc,
                exc_info=True,
            )
            raise

    async def close(self) -> None:
        """Close gRPC channel if open."""
        if self._channel:
            await self._channel.close()
            self._channel = None
            logger.info("ContextServiceAdapter channel closed")

