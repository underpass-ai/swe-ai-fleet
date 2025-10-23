from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class EventRecord:
    topic: str
    key: str
    payload: dict[str, Any]


class EventBusPort(Protocol):
    def publish(self, event: EventRecord) -> str: ...  # returns message id


