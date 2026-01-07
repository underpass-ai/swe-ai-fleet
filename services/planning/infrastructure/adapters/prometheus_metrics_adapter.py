"""Prometheus adapter for dual write metrics.

Following Hexagonal Architecture:
- Implements MetricsPort
- Exposes Prometheus metrics for dual write operations
- Metrics endpoint: /metrics
"""

import logging
from typing import Any

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, REGISTRY

from planning.application.ports.metrics_port import MetricsPort

logger = logging.getLogger(__name__)

# Error messages
_COUNT_NEGATIVE = "count cannot be negative"
_AGE_NEGATIVE = "age_seconds cannot be negative"


class PrometheusMetricsAdapter(MetricsPort):
    """Prometheus implementation of metrics port.

    Exposes metrics for dual write operations:
    - dualwrite_pending_count: Gauge with current pending operations count
    - dualwrite_pending_age_seconds: Histogram with pending operation ages
    - dualwrite_reconcile_attempts_total: Counter with total reconciliation attempts

    Following Hexagonal Architecture:
    - Infrastructure adapter implementing application port
    - No business logic, only metric recording
    """

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        """Initialize Prometheus metrics adapter.

        Creates Prometheus metrics:
        - dualwrite_pending_count (Gauge)
        - dualwrite_pending_age_seconds (Histogram)
        - dualwrite_reconcile_attempts_total (Counter)

        Args:
            registry: Optional custom registry (useful for testing).
                     If None, uses default REGISTRY.
        """
        self._registry = registry or REGISTRY

        # Gauge: Current number of pending operations
        self._pending_count = Gauge(
            name="dualwrite_pending_count",
            documentation="Current number of pending dual write operations",
            labelnames=[],
            registry=self._registry,
        )

        # Histogram: Age of pending operations (in seconds)
        self._pending_age = Histogram(
            name="dualwrite_pending_age_seconds",
            documentation="Age of pending dual write operations in seconds",
            buckets=[60, 300, 600, 1800, 3600, 7200, 14400, 28800],  # 1m, 5m, 10m, 30m, 1h, 2h, 4h, 8h
            registry=self._registry,
        )

        # Counter: Total reconciliation attempts
        self._reconcile_attempts = Counter(
            name="dualwrite_reconcile_attempts_total",
            documentation="Total number of reconciliation attempts",
            labelnames=[],
            registry=self._registry,
        )

        logger.info("PrometheusMetricsAdapter initialized")

    def record_pending_count(self, count: int) -> None:
        """Record the current number of pending operations.

        Args:
            count: Number of pending operations

        Raises:
            ValueError: If count is negative
        """
        if count < 0:
            raise ValueError(_COUNT_NEGATIVE)

        self._pending_count.set(count)

    def record_pending_age(self, age_seconds: float) -> None:
        """Record the age of a pending operation.

        Args:
            age_seconds: Age of pending operation in seconds

        Raises:
            ValueError: If age_seconds is negative
        """
        if age_seconds < 0:
            raise ValueError(_AGE_NEGATIVE)

        self._pending_age.observe(age_seconds)

    def increment_reconcile_attempts(self) -> None:
        """Increment the total number of reconciliation attempts."""
        self._reconcile_attempts.inc()
