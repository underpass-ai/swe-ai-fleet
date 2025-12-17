from dataclasses import dataclass

from core.orchestrator.domain.tasks.services.task_selection_service import Task, TaskSelectionService
from core.orchestrator.domain.tasks.task_status import TaskStatus


@dataclass
class MockTask:
    id: str
    title: str
    status: str


class TestTaskSelectionService:
    def test_pick_by_priority_returns_first_task(self) -> None:
        tasks: list[Task] = [
            MockTask(id="task-1", title="Task 1", status="READY"),
            MockTask(id="task-2", title="Task 2", status="READY"),
        ]

        result = TaskSelectionService.pick_by_priority(tasks)

        assert result == tasks[0]

    def test_filter_ready_tasks_includes_ready_and_in_progress(self) -> None:
        tasks: list[Task] = [
            MockTask(id="task-1", title="Task 1", status="READY"),
            MockTask(id="task-2", title="Task 2", status="IN_PROGRESS"),
            MockTask(id="task-3", title="Task 3", status="DONE"),
            MockTask(id="task-4", title="Task 4", status="FAILED"),
        ]

        result = TaskSelectionService.filter_ready_tasks(tasks)

        assert len(result) == 2
        assert result[0].id == "task-1"
        assert result[1].id == "task-2"

    def test_filter_ready_tasks_handles_case_insensitive_status(self) -> None:
        tasks: list[Task] = [
            MockTask(id="task-1", title="Task 1", status="ready"),
            MockTask(id="task-2", title="Task 2", status="in_progress"),
        ]

        result = TaskSelectionService.filter_ready_tasks(tasks)

        assert len(result) == 2

    def test_select_task_pick_first_returns_first_ready(self) -> None:
        tasks: list[Task] = [
            MockTask(id="task-1", title="Task 1", status="READY"),
            MockTask(id="task-2", title="Task 2", status="READY"),
        ]

        result = TaskSelectionService.select_task(tasks, pick_first=True)

        assert result is not None
        assert result.id == "task-1"

    def test_select_task_pick_first_returns_none_when_no_ready_tasks(self) -> None:
        tasks: list[Task] = [
            MockTask(id="task-1", title="Task 1", status="DONE"),
            MockTask(id="task-2", title="Task 2", status="FAILED"),
        ]

        result = TaskSelectionService.select_task(tasks, pick_first=True)

        assert result is None

    def test_select_task_priority_mode_uses_pick_by_priority(self) -> None:
        tasks: list[Task] = [
            MockTask(id="task-1", title="Task 1", status="READY"),
            MockTask(id="task-2", title="Task 2", status="READY"),
        ]

        result = TaskSelectionService.select_task(tasks, pick_first=False)

        assert result is not None
        assert result.id == "task-1"
