"""RetryPolicy: Value Object representing retry configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    """
    Value Object: Retry policy configuration.

    Domain Invariants:
    - max_attempts must be >= 1
    - backoff_seconds must be >= 0
    - exponential_backoff is a boolean flag
    - Immutable (frozen=True)

    Business Rules:
    - Defines how steps should be retried on failure
    - Used by steps that can fail and need retry logic
    """

    max_attempts: int
    backoff_seconds: int
    exponential_backoff: bool = False

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Raises:
            ValueError: If retry policy is invalid
        """
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1: {self.max_attempts}")

        if self.backoff_seconds < 0:
            raise ValueError(f"backoff_seconds must be >= 0: {self.backoff_seconds}")
