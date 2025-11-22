"""ExecutionPlan value object."""

from __future__ import annotations

from dataclasses import dataclass

from .execution_step import ExecutionStep
from .task_node import TaskNode


@dataclass(frozen=True)
class ExecutionPlan:
    """Sequential order of tasks for execution."""

    steps: tuple[ExecutionStep, ...]

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValueError("ExecutionPlan cannot be empty")

        expected = 0
        for step in self.steps:
            if step.order != expected:
                raise ValueError("ExecutionPlan steps must be contiguous starting at 0")
            expected += 1

    @property
    def tasks(self) -> tuple[TaskNode, ...]:
        return tuple(step.task for step in self.steps)

    def __iter__(self):
        return iter(self.steps)

    def __len__(self) -> int:
        return len(self.steps)

