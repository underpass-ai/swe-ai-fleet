"""Redis adapter (read + save) depending on a Redis KV/Stream port."""

import json
from typing import Any

from swe_ai_fleet.memory.redis_store import RedisKvPort
from swe_ai_fleet.reports.domain.report import Report
from swe_ai_fleet.reports.dtos.dtos import (
    CaseSpecDTO,
    PlanningEventDTO,
    PlanVersionDTO,
    SubtaskPlanDTO,
)
from swe_ai_fleet.reports.ports.planning_read_port import PlanningReadPort


class RedisPlanningReadAdapter(PlanningReadPort):
    def __init__(self, client: RedisKvPort) -> None:
        self.r = client

    @staticmethod
    def _k_spec(case_id: str) -> str:
        return f"swe:case:{case_id}:spec"

    @staticmethod
    def _k_draft(case_id: str) -> str:
        return f"swe:case:{case_id}:planning:draft"

    @staticmethod
    def _k_stream(case_id: str) -> str:
        return f"swe:case:{case_id}:planning:stream"

    @staticmethod
    def _k_report_list(case_id: str) -> str:
        return f"swe:case:{case_id}:reports:implementation:ids"

    @staticmethod
    def _k_report_doc(case_id: str, report_id: str) -> str:
        return f"swe:case:{case_id}:reports:implementation:{report_id}"

    @staticmethod
    def _k_report_last(case_id: str) -> str:
        return f"swe:case:{case_id}:reports:implementation:last"

    def get_case_spec(self, case_id: str) -> CaseSpecDTO | None:
        raw = self.r.get(self._k_spec(case_id))
        if not raw:
            return None
        data = json.loads(raw)
        return CaseSpecDTO(
            case_id=data["case_id"],
            title=data["title"],
            description=data.get("description", ""),
            acceptance_criteria=list(data.get("acceptance_criteria", [])),
            constraints=dict(data.get("constraints", {})),
            requester_id=data.get("requester_id", ""),
            tags=list(data.get("tags", [])),
            created_at_ms=int(data.get("created_at_ms", 0)),
        )

    def get_plan_draft(self, case_id: str) -> PlanVersionDTO | None:
        raw = self.r.get(self._k_draft(case_id))
        if not raw:
            return None
        data = json.loads(raw)
        subs: list[SubtaskPlanDTO] = []
        for st in data.get("subtasks", []):
            subs.append(
                SubtaskPlanDTO(
                    subtask_id=st["subtask_id"],
                    title=st["title"],
                    description=st.get("description", ""),
                    role=st["role"],
                    suggested_tech=list(st.get("suggested_tech", [])),
                    depends_on=list(st.get("depends_on", [])),
                    estimate_points=float(st.get("estimate_points", 0.0)),
                    priority=int(st.get("priority", 0)),
                    risk_score=float(st.get("risk_score", 0.0)),
                    notes=st.get("notes", ""),
                )
            )
        return PlanVersionDTO(
            plan_id=data["plan_id"],
            case_id=data["case_id"],
            version=int(data["version"]),
            status=str(data["status"]),
            author_id=data["author_id"],
            rationale=data.get("rationale", ""),
            subtasks=subs,
            created_at_ms=int(data.get("created_at_ms", 0)),
        )

    def get_planning_events(self, case_id: str, count: int = 200) -> list[PlanningEventDTO]:
        key = self._k_stream(case_id)
        entries = self.r.xrevrange(key, count=count)  # newest-first
        out: list[PlanningEventDTO] = []
        for msg_id, fields in reversed(entries):
            payload: dict[str, Any] = {}
            try:
                payload = json.loads(fields.get("payload", "{}"))
            except Exception:
                payload = {"raw": fields.get("payload")}
            out.append(
                PlanningEventDTO(
                    id=msg_id,
                    event=fields.get("event", ""),
                    actor=fields.get("actor", ""),
                    payload=payload,
                    ts_ms=int(fields.get("ts", "0")),
                )
            )
        return out

    def save_report(self, case_id: str, report: Report, ttl_seconds: int) -> None:
        report_id = f"{report.generated_at_ms}"
        key_doc = self._k_report_doc(case_id, report_id)
        key_list = self._k_report_list(case_id)
        key_last = self._k_report_last(case_id)
        doc = {
            "case_id": report.case_id,
            "plan_id": report.plan_id or "",
            "generated_at_ms": report.generated_at_ms,
            "markdown": report.markdown,
            "stats": report.stats,
        }
        pipe = self.r.pipeline()
        pipe.set(key_doc, json.dumps(doc), ex=ttl_seconds)
        pipe.lpush(key_list, report_id)
        pipe.set(key_last, report_id, ex=ttl_seconds)
        # soft-expire list as well (not critical)
        pipe.expire(key_list, ttl_seconds)
        pipe.execute()
