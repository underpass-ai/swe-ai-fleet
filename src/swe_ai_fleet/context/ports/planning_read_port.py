from typing import Any, Protocol

from swe_ai_fleet.reports.dtos.dtos import (
    CaseSpecDTO,
    PlanningEventDTO,
    PlanVersionDTO,
)


class PlanningReadPort(Protocol):
    def get_case_spec(self, case_id: str) -> CaseSpecDTO | None: ...
    def get_plan_draft(self, case_id: str) -> PlanVersionDTO | None: ...

    def get_planning_events(self, case_id: str, count: int = 200) -> list[PlanningEventDTO]: ...

    # Optional: store handoff bundle for debugging/traceability

    def save_handoff_bundle(self, case_id: str, bundle: dict[str, Any], ttl_seconds: int) -> None: ...
