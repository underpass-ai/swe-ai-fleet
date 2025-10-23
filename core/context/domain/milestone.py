from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Milestone:
    ts_ms: int
    event: str
    actor: str

    def to_dict(self) -> dict[str, Any]:
        return {"ts_ms": self.ts_ms, "event": self.event, "actor": self.actor}
