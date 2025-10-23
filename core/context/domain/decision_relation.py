from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DecisionRelation:
    src: str
    rel: str
    dst: str

    def to_dict(self) -> dict[str, Any]:
        return {"src": self.src, "rel": self.rel, "dst": self.dst}
