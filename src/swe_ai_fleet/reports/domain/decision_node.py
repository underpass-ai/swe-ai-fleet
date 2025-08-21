from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionNode:
    id: str
    title: str
    rationale: str
    status: str
    created_at_ms: int
    author_id: str
