"""Port for Valkey validation operations."""

from typing import Protocol


class ValkeyValidatorPort(Protocol):
    """Interface for Valkey (Redis) validation."""

    async def validate_key_exists(self, key: str) -> bool:
        """Validate that a key exists in Valkey.
        
        Args:
            key: Key to check
            
        Returns:
            True if key exists
            
        Raises:
            AssertionError: If key does not exist
        """
        ...

    async def validate_hash_field(
        self,
        key: str,
        field: str,
        expected_value: str | None = None
    ) -> str:
        """Validate that a hash field exists and optionally matches expected value.
        
        Args:
            key: Hash key
            field: Field name
            expected_value: Optional expected value
            
        Returns:
            Actual field value
            
        Raises:
            AssertionError: If validation fails
        """
        ...

    async def validate_task_context_exists(
        self,
        task_id: str,
        required_fields: list[str]
    ) -> dict[str, str]:
        """Validate that task context exists with required fields.
        
        Args:
            task_id: Task identifier
            required_fields: Fields that must exist
            
        Returns:
            Task context data
            
        Raises:
            AssertionError: If validation fails
        """
        ...

    async def cleanup_keys(self, pattern: str) -> int:
        """Clean up keys matching pattern (for test isolation).
        
        Args:
            pattern: Redis key pattern (e.g., "test:*")
            
        Returns:
            Number of keys deleted
        """
        ...

