import json
import time
from typing import Any, cast

import redis

from swe_ai_fleet.reports.dtos.dtos import (
    CaseSpecDTO,
    PlanningEventDTO,
    PlanVersionDTO,
    SubtaskPlanDTO,
)

from ..ports.planning_read_port import PlanningReadPort


class RedisPlanningReadAdapter(PlanningReadPort):
    def __init__(self, url: str) -> None:
        self.r = redis.Redis.from_url(url, decode_responses=True)

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
    def _k_summary_last(case_id: str) -> str:
        return f"swe:case:{case_id}:summaries:last"  # optional convention

    @staticmethod
    def _k_handoff(case_id: str, ts: int) -> str:
        return f"swe:case:{case_id}:handoff:{ts}"

    def get_case_spec(self, case_id: str) -> CaseSpecDTO | None:
        raw = self.r.get(self._k_spec(case_id))
        if not raw:
            return None
        text = cast(str, raw)
        d = json.loads(text)
        return CaseSpecDTO(
            case_id=d["case_id"],
            title=d["title"],
            description=d.get("description", ""),
            acceptance_criteria=list(d.get("acceptance_criteria", [])),
            constraints=dict(d.get("constraints", {})),
            requester_id=d.get("requester_id", ""),
            tags=list(d.get("tags", [])),
            created_at_ms=int(d.get("created_at_ms", 0)),
        )

    def get_plan_draft(self, case_id: str) -> PlanVersionDTO | None:
        raw = self.r.get(self._k_draft(case_id))
        if not raw:
            return None
        text = cast(str, raw)
        d = json.loads(text)
        subs: list[SubtaskPlanDTO] = []
        for st in d.get("subtasks", []):
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
            plan_id=d["plan_id"],
            case_id=d["case_id"],
            version=int(d["version"]),
            status=str(d["status"]),
            author_id=d["author_id"],
            rationale=d.get("rationale", ""),
            subtasks=subs,
            created_at_ms=int(d.get("created_at_ms", 0)),
        )

    def get_planning_events(self, case_id: str, count: int = 200) -> list[PlanningEventDTO]:
        # Redis returns latest-first for XREVRANGE; ensure chronological order
        # regardless of backend/fake behavior by explicitly sorting by ts.
        entries_raw: Any = self.r.xrevrange(self._k_stream(case_id), count=count)
        entries = list(cast(list[tuple[str, dict[str, Any]]], entries_raw))
        # Normalize to chronological order using the provided timestamp field.
        entries.sort(key=lambda item: int(item[1].get("ts", "0")))
        out: list[PlanningEventDTO] = []
        for msg_id, fields in entries:
            try:
                payload_text = fields.get("payload", "{}")
                payload = json.loads(payload_text)
            except json.JSONDecodeError:
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

    def read_last_summary(self, case_id: str) -> str | None:
        raw = self.r.get(self._k_summary_last(case_id))
        return cast(str | None, raw if raw else None)

    def save_handoff_bundle(self, case_id: str, bundle: dict[str, Any], ttl_seconds: int) -> None:
        ts = int(time.time() * 1000)
        self.r.set(self._k_handoff(case_id, ts), json.dumps(bundle), ex=ttl_seconds)
