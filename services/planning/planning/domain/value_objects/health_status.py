"""HealthStatus enum for service health."""

from enum import Enum


class HealthStatus(str, Enum):
    """Enumeration of service health statuses.

    Following DDD:
    - Enum for fixed set of values
    - Type-safe health indicators
    - NO magic strings
    """

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        """String representation.

        Returns:
            Status value
        """
        return self.value

    def is_healthy(self) -> bool:
        """Check if status is healthy.

        Tell, Don't Ask: Status knows if it's healthy.

        Returns:
            True if HEALTHY
        """
        return self == HealthStatus.HEALTHY

