from typing import Protocol

from swe_ai_fleet.reports.domain.report import Report
from swe_ai_fleet.reports.dtos.dtos import (
    CaseSpecDTO,
    PlanningEventDTO,
    PlanVersionDTO,
)


class PlanningReadPort(Protocol):
    def get_case_spec(self, case_id: str) -> CaseSpecDTO | None: ...
    def get_plan_draft(self, case_id: str) -> PlanVersionDTO | None: ...
    def get_planning_events(self, case_id: str, count: int = 200) -> list[PlanningEventDTO]: ...
    def save_report(self, case_id: str, report: Report, ttl_seconds: int) -> None: ...
