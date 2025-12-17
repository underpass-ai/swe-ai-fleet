"""Typed representation of a deliberation registry entry."""

from typing import TypedDict

from services.ray_executor.domain.entities import (
    DeliberationResult,
    MultiAgentDeliberationResult,
)


class DeliberationRegistryEntry(TypedDict, total=False):
    """In-memory state for a single deliberation tracked by the service.

    This lives in the application layer and represents the mutable
    registry entry used to track deliberation lifecycle and results.

    It is intentionally not a domain entity (domain entities are immutable),
    but it provides stronger typing than a raw dict.
    """

    status: str
    start_time: float
    end_time: float
    result: DeliberationResult | MultiAgentDeliberationResult | None
    error: str | None

