from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DecisionNode:
    id: str
    title: str
    rationale: str
    status: str
    created_at_ms: int
    author_id: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize decision node to a plain dict."""
        return {
            "id": self.id,
            "title": self.title,
            "rationale": self.rationale,
            "status": self.status,
            "author_id": self.author_id,
            "created_at_ms": self.created_at_ms,
        }
