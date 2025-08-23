from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CaseHeader:
    case_id: str
    title: str
    constraints: dict[str, Any]
    acceptance_criteria: list[str]
    tags: list[str]

    @staticmethod
    def from_spec(spec: Any) -> CaseHeader:
        return CaseHeader(
            case_id=spec.case_id,
            title=spec.title,
            constraints=spec.constraints,
            acceptance_criteria=spec.acceptance_criteria,
            tags=spec.tags,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "constraints": self.constraints,
            "acceptance_criteria": self.acceptance_criteria,
            "tags": self.tags,
        }
