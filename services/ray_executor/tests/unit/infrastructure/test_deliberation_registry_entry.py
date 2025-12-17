"""Unit tests for RayDeliberationRegistryEntry infrastructure type."""

from typing import Any, get_type_hints

from services.ray_executor.infrastructure.deliberation_registry_entry import (
    RayDeliberationRegistryEntry,
)


def test_ray_deliberation_registry_entry_has_expected_fields() -> None:
    """Ensure RayDeliberationRegistryEntry exposes the expected keys."""
    hints = get_type_hints(RayDeliberationRegistryEntry)

    expected_keys = {
        "status",
        "start_time",
        "end_time",
        "error",
        "futures",
        "future",
        "task_id",
        "role",
        "agents",
        "total_agents",
    }

    assert expected_keys.issubset(hints.keys())


def test_ray_deliberation_registry_entry_allows_partial_entries() -> None:
    """TypedDict is declared with total=False so partial entries are valid."""
    entry: RayDeliberationRegistryEntry = {
        "status": "running",
        "start_time": 123.0,
        "task_id": "task-1",
        "role": "DEV",
    }

    # At runtime this is just a dict; we assert the structure we care about.
    assert entry["status"] == "running"
    assert entry["task_id"] == "task-1"
    assert "end_time" not in entry

