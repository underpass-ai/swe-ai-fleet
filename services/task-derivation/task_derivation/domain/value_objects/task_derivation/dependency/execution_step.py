"""ExecutionStep value object."""

from __future__ import annotations

from dataclasses import dataclass

from .task_node import TaskNode


@dataclass(frozen=True)
class ExecutionStep:
    """Represents a single sequential execution step."""

    order: int
    task: TaskNode

    def __post_init__(self) -> None:
        if self.order < 0:
            raise ValueError("ExecutionStep order must be >= 0")

