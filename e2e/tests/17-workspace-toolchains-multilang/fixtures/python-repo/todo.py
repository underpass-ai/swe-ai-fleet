from dataclasses import dataclass
from typing import Optional


@dataclass
class Todo:
    id: int
    title: str
    done: bool = False
    completed_at: Optional[str] = None


def add_todo(items: list[Todo], title: str) -> list[Todo]:
    next_id = len(items) + 1
    return [*items, Todo(id=next_id, title=title)]


def complete_todo(items: list[Todo], item_id: int, completed_at: str) -> bool:
    for item in items:
        if item.id == item_id:
            item.done = True
            item.completed_at = completed_at
            return True
    return False


def pending_count(items: list[Todo]) -> int:
    return len([item for item in items if not item.done])
