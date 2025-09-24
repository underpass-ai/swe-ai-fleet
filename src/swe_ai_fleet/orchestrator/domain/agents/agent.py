from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..tasks.task_constraints import TaskConstraints


class Agent:
    def generate(self, task: str, constraints: TaskConstraints, diversity: bool) -> dict[str, Any]:
        raise NotImplementedError

    def critique(self, proposal: str, rubric: dict[str, Any]) -> str:
        raise NotImplementedError

    def revise(self, content: str, feedback: str) -> str:
        raise NotImplementedError