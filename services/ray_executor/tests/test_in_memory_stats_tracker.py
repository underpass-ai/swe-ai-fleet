from __future__ import annotations

from typing import Any

import pytest

from services.ray_executor.infrastructure.adapters.in_memory_stats_tracker import (
    InMemoryStatsTrackerAdapter,
)


@pytest.fixture
def base_stats() -> dict[str, Any]:
    return {
        "total_deliberations": 0,
        "active_deliberations": 0,
        "completed_deliberations": 0,
        "failed_deliberations": 0,
        "execution_times": [],
    }


def test_increment_active_updates_total_and_active(base_stats: dict[str, Any]) -> None:
    tracker = InMemoryStatsTrackerAdapter(stats=base_stats)

    tracker.increment_active()
    tracker.increment_active()

    assert base_stats["active_deliberations"] == 2
    assert base_stats["total_deliberations"] == 2


def test_decrement_active_never_goes_below_zero(base_stats: dict[str, Any]) -> None:
    tracker = InMemoryStatsTrackerAdapter(stats=base_stats)

    tracker.decrement_active()
    assert base_stats["active_deliberations"] == 0

    tracker.increment_active()
    tracker.decrement_active()
    assert base_stats["active_deliberations"] == 0


def test_record_completed_appends_time_and_increments_completed(base_stats: dict[str, Any]) -> None:
    tracker = InMemoryStatsTrackerAdapter(stats=base_stats)

    tracker.record_completed(1.5)
    tracker.record_completed(2.0)

    assert base_stats["completed_deliberations"] == 2
    assert base_stats["execution_times"] == [1.5, 2.0]


def test_record_failed_increments_failed(base_stats: dict[str, Any]) -> None:
    tracker = InMemoryStatsTrackerAdapter(stats=base_stats)

    tracker.record_failed()
    tracker.record_failed()

    assert base_stats["failed_deliberations"] == 2
