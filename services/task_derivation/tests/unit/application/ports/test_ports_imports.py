"""Smoke tests ensuring ports are importable."""

from __future__ import annotations

from task_derivation.application.ports import (
    ContextPort,
    MessagingPort,
    PlanningPort,
    RayExecutorPort,
)


def test_ports_are_importable() -> None:
    """Ensure modules expose the expected names."""
    assert ContextPort.__name__ == "ContextPort"
    assert MessagingPort.__name__ == "MessagingPort"
    assert PlanningPort.__name__ == "PlanningPort"
    assert RayExecutorPort.__name__ == "RayExecutorPort"

