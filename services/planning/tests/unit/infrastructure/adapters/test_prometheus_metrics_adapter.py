"""Unit tests for PrometheusMetricsAdapter."""

import pytest
from prometheus_client import CollectorRegistry

from planning.application.ports.metrics_port import MetricsPort
from planning.infrastructure.adapters.prometheus_metrics_adapter import (
    PrometheusMetricsAdapter,
)


class TestPrometheusMetricsAdapter:
    """Tests for PrometheusMetricsAdapter."""

    def test_init(self) -> None:
        """Test adapter initialization."""
        registry = CollectorRegistry()
        adapter = PrometheusMetricsAdapter(registry=registry)
        assert adapter is not None
        assert isinstance(adapter, MetricsPort)

    def test_record_pending_count(self) -> None:
        """Test recording pending count."""
        registry = CollectorRegistry()
        adapter = PrometheusMetricsAdapter(registry=registry)
        adapter.record_pending_count(5)
        # Prometheus metrics are side-effects, just verify no exception

    def test_record_pending_count_negative_raises(self) -> None:
        """Test recording negative pending count raises ValueError."""
        registry = CollectorRegistry()
        adapter = PrometheusMetricsAdapter(registry=registry)
        with pytest.raises(ValueError, match="count cannot be negative"):
            adapter.record_pending_count(-1)

    def test_record_pending_age(self) -> None:
        """Test recording pending age."""
        registry = CollectorRegistry()
        adapter = PrometheusMetricsAdapter(registry=registry)
        adapter.record_pending_age(60.5)
        # Prometheus metrics are side-effects, just verify no exception

    def test_record_pending_age_negative_raises(self) -> None:
        """Test recording negative pending age raises ValueError."""
        registry = CollectorRegistry()
        adapter = PrometheusMetricsAdapter(registry=registry)
        with pytest.raises(ValueError, match="age_seconds cannot be negative"):
            adapter.record_pending_age(-1.0)

    def test_increment_reconcile_attempts(self) -> None:
        """Test incrementing reconcile attempts."""
        registry = CollectorRegistry()
        adapter = PrometheusMetricsAdapter(registry=registry)
        adapter.increment_reconcile_attempts()
        adapter.increment_reconcile_attempts()
        # Prometheus metrics are side-effects, just verify no exception
