"""TopologyNode value object."""

from __future__ import annotations

from dataclasses import dataclass

from .task_node import TaskNode


@dataclass(frozen=True)
class TopologyNode:
    """Represents dependency metadata for a single task."""

    task: TaskNode
    in_degree: int
    prerequisites: frozenset[str]

    def __post_init__(self) -> None:
        if self.in_degree < 0:
            raise ValueError("in_degree cannot be negative")

    def is_ready(self) -> bool:
        return self.in_degree == 0

    def remove_dependency(self, prerequisite_id: str) -> TopologyNode:
        if prerequisite_id not in self.prerequisites:
            return self

        return TopologyNode(
            task=self.task,
            in_degree=max(self.in_degree - 1, 0),
            prerequisites=frozenset(
                prereq for prereq in self.prerequisites if prereq != prerequisite_id
            ),
        )

