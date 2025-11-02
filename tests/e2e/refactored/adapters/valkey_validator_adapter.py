"""Valkey (Redis) validator adapter."""

import redis.asyncio as redis


class ValkeyValidatorAdapter:
    """Adapter for validating Valkey (Redis) data."""

    def __init__(self, host: str, port: int, db: int = 0) -> None:
        """Initialize adapter.
        
        Args:
            host: Valkey host
            port: Valkey port
            db: Database number (default: 0)
        """
        if not host:
            raise ValueError("host cannot be empty")
        if port < 1 or port > 65535:
            raise ValueError(f"invalid port: {port}")

        self._host = host
        self._port = port
        self._db = db
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """Establish connection to Valkey."""
        self._client = redis.Redis(
            host=self._host,
            port=self._port,
            db=self._db,
            decode_responses=True
        )

    async def close(self) -> None:
        """Close connection."""
        if self._client:
            await self._client.close()

    async def validate_key_exists(self, key: str) -> bool:
        """Validate that a key exists in Valkey."""
        if not self._client:
            raise RuntimeError("Adapter not connected. Call connect() first.")

        exists = await self._client.exists(key)
        if not exists:
            raise AssertionError(f"Key does not exist: {key}")

        return True

    async def validate_hash_field(
        self,
        key: str,
        field: str,
        expected_value: str | None = None
    ) -> str:
        """Validate that a hash field exists and optionally matches expected value."""
        if not self._client:
            raise RuntimeError("Adapter not connected. Call connect() first.")

        value = await self._client.hget(key, field)

        if value is None:
            raise AssertionError(f"Field '{field}' does not exist in hash '{key}'")

        if expected_value is not None and value != expected_value:
            raise AssertionError(
                f"Field '{field}' value mismatch: expected '{expected_value}', got '{value}'"
            )

        return value

    async def validate_task_context_exists(
        self,
        task_id: str,
        required_fields: list[str]
    ) -> dict[str, str]:
        """Validate that task context exists with required fields."""
        if not self._client:
            raise RuntimeError("Adapter not connected. Call connect() first.")

        key = f"task:{task_id}:context"

        # Check if key exists
        exists = await self._client.exists(key)
        if not exists:
            raise AssertionError(f"Task context does not exist: {key}")

        # Get all hash fields
        context_data = await self._client.hgetall(key)

        # Validate required fields
        missing_fields = [f for f in required_fields if f not in context_data]
        if missing_fields:
            raise AssertionError(
                f"Missing required fields in task context: {missing_fields}"
            )

        return context_data

    async def cleanup_keys(self, pattern: str) -> int:
        """Clean up keys matching pattern (for test isolation)."""
        if not self._client:
            raise RuntimeError("Adapter not connected. Call connect() first.")

        # Find keys matching pattern
        keys = []
        async for key in self._client.scan_iter(match=pattern):
            keys.append(key)

        # Delete keys
        if keys:
            return await self._client.delete(*keys)

        return 0

