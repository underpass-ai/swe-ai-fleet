"""Infrastructure type for deliberation registry entries."""

from __future__ import annotations

from typing import Any, TypedDict


class RayDeliberationRegistryEntry(TypedDict, total=False):
    """In-memory registry entry for a Ray deliberation.

    This type is used only in the infrastructure layer to model the
    mutable state kept for each deliberation while it is executing
    on the Ray cluster.
    """

    # Core tracking fields
    status: str
    start_time: float
    end_time: float
    error: str | None

    # Ray execution metadata
    futures: list[Any]
    future: Any  # Backward-compatibility for single-future format
    task_id: str
    role: str
    agents: list[str]
    total_agents: int

