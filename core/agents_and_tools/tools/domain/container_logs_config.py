"""Container logs configuration value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ContainerLogsConfig:
    """
    Immutable value object representing container logs configuration.

    Following DDD principles:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - Self-contained business logic
    """

    container: str
    tail: Optional[int] = None
    follow: bool = False
    timeout: int = 60

    def __post_init__(self) -> None:
        """
        Validate value object invariants (fail-fast).

        Raises:
            ValueError: If any invariant is violated
        """
        if not self.container or not self.container.strip():
            raise ValueError("container is required and cannot be empty (fail-fast)")

        if self.tail is not None:
            if not isinstance(self.tail, int):
                raise ValueError("tail must be an integer or None (fail-fast)")
            if self.tail <= 0:
                raise ValueError("tail must be positive (fail-fast)")

        if not isinstance(self.follow, bool):
            raise ValueError("follow must be a boolean (fail-fast)")

        if not isinstance(self.timeout, int):
            raise ValueError("timeout must be an integer (fail-fast)")

        if self.timeout <= 0:
            raise ValueError("timeout must be positive (fail-fast)")

    def has_tail_limit(self) -> bool:
        """
        Check if tail limit is specified.

        Returns:
            True if tail is set, False otherwise
        """
        return self.tail is not None

    def is_following(self) -> bool:
        """
        Check if logs should be followed (streamed).

        Returns:
            True if follow mode is enabled
        """
        return self.follow

    def should_stream(self) -> bool:
        """
        Check if logs should be streamed continuously.

        Alias for is_following() for better readability.

        Returns:
            True if follow mode is enabled
        """
        return self.is_following()

    @classmethod
    def all_logs(cls, container: str) -> ContainerLogsConfig:
        """
        Create config to fetch all logs (no tail limit).

        Args:
            container: Container name or ID

        Returns:
            ContainerLogsConfig for all logs
        """
        return cls(container=container, tail=None, follow=False)

    @classmethod
    def recent_logs(cls, container: str, tail: int = 100) -> ContainerLogsConfig:
        """
        Create config to fetch recent logs (with tail limit).

        Args:
            container: Container name or ID
            tail: Number of recent lines to fetch

        Returns:
            ContainerLogsConfig for recent logs
        """
        return cls(container=container, tail=tail, follow=False)

    @classmethod
    def follow_logs(cls, container: str, tail: Optional[int] = None) -> ContainerLogsConfig:
        """
        Create config to follow logs (streaming mode).

        Args:
            container: Container name or ID
            tail: Optional number of lines to start with

        Returns:
            ContainerLogsConfig for following logs
        """
        return cls(container=container, tail=tail, follow=True)

