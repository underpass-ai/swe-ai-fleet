"""DeliberationId value object for Ray Executor tracking."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeliberationId:
    """Value Object for Ray Executor deliberation identifier.

    Used to track async LLM generation jobs in Ray cluster.
    Domain Invariant: DeliberationId cannot be empty.
    Following DDD: No primitives - everything is a value object.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate DeliberationId (fail-fast).

        Raises:
            ValueError: If deliberation ID is empty or whitespace
        """
        if not self.value or not self.value.strip():
            raise ValueError("DeliberationId cannot be empty")

    def __str__(self) -> str:
        """String representation.

        Returns:
            String value
        """
        return self.value

