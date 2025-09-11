"""Redis adapter (read + save) depending on a Redis KV/Stream port.

Extended with optional helpers to surface LLM conversation streams
stored by ``RedisStoreImpl`` under per-session keys.
These helpers are best-effort and rely on common Redis commands
if the underlying client supports them.
"""

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

    # ---- Optional helpers: LLM session streams ----

    @staticmethod
    def _k_session_meta(session_id: str) -> str:
        return f"swe:session:{session_id}:meta"

    @staticmethod
    def _k_session_stream(session_id: str) -> str:
        return f"swe:session:{session_id}:stream"

    def list_llm_sessions_for_case(
        self, case_id: str, max_sessions: int = 20
    ) -> list[tuple[str, dict[str, Any]]]:
        """Return up to ``max_sessions`` (session_id, meta) for sessions tagged with this case.

        Requires the underlying Redis client to implement SCAN and HGETALL.
        Falls back to KEYS if SCAN is unavailable (not recommended for very large DBs).
        """
        sessions: list[tuple[str, dict[str, Any]]] = []
        client: Any = self.r  # duck-typing
        # Discover meta keys
        meta_keys: list[str] = []
        if hasattr(client, "scan"):
            cursor = 0
            match = "swe:session:*:meta"
            while True:
                cursor, keys = client.scan(cursor=cursor, match=match, count=500)
                meta_keys.extend(keys or [])
                if cursor == 0 or len(meta_keys) >= max_sessions * 3:
                    break
        elif hasattr(client, "keys"):
            try:
                meta_keys = list(client.keys("swe:session:*:meta"))  # type: ignore[arg-type]
            except Exception:
                meta_keys = []

        for key in meta_keys:
            if len(sessions) >= max_sessions:
                break
            try:
                meta: dict[str, Any] = {}
                if hasattr(client, "hgetall"):
                    meta = client.hgetall(key)
                else:
                    # Best-effort: attempt pipeline HGETs
                    case_val = client.hget(key, "case_id") if hasattr(client, "hget") else None
                    created_at = client.hget(key, "created_at") if hasattr(client, "hget") else None
                    role = client.hget(key, "role") if hasattr(client, "hget") else None
                    meta = {"case_id": case_val, "created_at": created_at, "role": role}
                if str(meta.get("case_id")) != case_id:
                    continue
                # extract session id
                # format: swe:session:{session_id}:meta
                sid = str(key).split(":")[2] if isinstance(key, str) else ""
                sessions.append((sid, meta))
            except Exception:
                continue
        return sessions

    def get_llm_events_for_session(self, session_id: str, count: int = 20) -> list[dict[str, Any]]:
        """Return last ``count`` events for a session stream as dictionaries.

        Uses XREVRANGE for newest-first then reverses to chronological order.
        """
        out: list[dict[str, Any]] = []
        try:
            entries = self.r.xrevrange(self._k_session_stream(session_id), count=count)
            for msg_id, fields in reversed(entries):
                rec: dict[str, Any] = {"id": msg_id}
                rec.update(fields)
                out.append(rec)
        except Exception:
            return []
        return out
