from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Report:
    case_id: str
    plan_id: str | None
    generated_at_ms: int
    markdown: str
    stats: dict[str, Any] = field(default_factory=dict)
