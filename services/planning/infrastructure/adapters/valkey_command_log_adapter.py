"""Valkey (Redis-compatible) adapter for CommandLogPort.

Provides command response caching for gRPC idempotency using Valkey.
Key format: planning:cmd:{request_id} → serialized response bytes

Following Hexagonal Architecture:
- This is an ADAPTER (infrastructure implementation)
- Implements CommandLogPort (application port)
- Uses Valkey for persistence (external dependency)
"""

import asyncio
import logging
from typing import cast

import valkey  # Valkey is Redis-compatible (synchronous client)

from planning.application.ports.command_log_port import CommandLogPort
from planning.infrastructure.adapters.valkey_config import ValkeyConfig

logger = logging.getLogger(__name__)

# Error messages
ERROR_REQUEST_ID_EMPTY = "request_id cannot be empty"


class ValkeyCommandLogAdapter(CommandLogPort):
    """Valkey adapter for command log (gRPC idempotency).

    Stores command responses in Valkey for idempotent gRPC operations.
    Key format: planning:cmd:{request_id}
    Storage: Permanent (no TTL by default) to prevent duplicate executions
    """

    def __init__(self, config: ValkeyConfig | None = None) -> None:
        """Initialize Valkey command log adapter.

        Args:
            config: Valkey configuration (optional, uses default if not provided)
        """
        self.config = config or ValkeyConfig()

        # Create Valkey client (Redis-compatible)
        self.client = valkey.Valkey(
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            decode_responses=False,  # Store raw bytes for protobuf responses
        )

        # Test connection
        self.client.ping()

        logger.info(
            f"Valkey command log adapter initialized: {self.config.host}:{self.config.port}"
        )

    def close(self) -> None:
        """Close Valkey connection."""
        self.client.close()
        logger.info("Valkey command log adapter connection closed")

    def _command_log_key(self, request_id: str) -> str:
        """Generate command log key for request_id.

        Args:
            request_id: Unique request identifier

        Returns:
            Redis key: planning:cmd:{request_id}
        """
        return f"planning:cmd:{request_id}"

    async def get_response(
        self,
        request_id: str,
    ) -> bytes | None:
        """Get cached response for a request_id.

        Args:
            request_id: Unique request identifier

        Returns:
            Serialized response bytes if found, None otherwise

        Raises:
            ValueError: If request_id is empty
            Exception: If storage operation fails
        """
        if not request_id or not request_id.strip():
            raise ValueError(ERROR_REQUEST_ID_EMPTY)

        key = self._command_log_key(request_id.strip())

        try:
            response_bytes = await asyncio.to_thread(self.client.get, key)
            if response_bytes is None:
                logger.debug(f"Command log miss: {request_id}")
                return None

            logger.info(f"Command log hit: {request_id}")
            return cast(bytes, response_bytes)

        except Exception as e:
            logger.error(f"Failed to get command log for {request_id}: {e}", exc_info=True)
            raise

    async def store_response(
        self,
        request_id: str,
        response_bytes: bytes,
    ) -> None:
        """Store response for a request_id.

        Args:
            request_id: Unique request identifier
            response_bytes: Serialized response to store

        Raises:
            ValueError: If request_id is empty
            Exception: If storage operation fails
        """
        if not request_id or not request_id.strip():
            raise ValueError(ERROR_REQUEST_ID_EMPTY)

        if not response_bytes:
            raise ValueError("response_bytes cannot be empty")

        key = self._command_log_key(request_id.strip())

        try:
            # Store response permanently (no TTL) to prevent duplicate executions
            await asyncio.to_thread(self.client.set, key, response_bytes)
            logger.info(f"Command log stored: {request_id}")

        except Exception as e:
            logger.error(f"Failed to store command log for {request_id}: {e}", exc_info=True)
            raise
