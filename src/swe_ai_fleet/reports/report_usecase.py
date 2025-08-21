from __future__ import annotations

import time
from typing import Any

from swe_ai_fleet.reports.domain.report import Report
from swe_ai_fleet.reports.domain.report_request import ReportRequest
from swe_ai_fleet.reports.dtos.dtos import (
    CaseSpecDTO,
    PlanningEventDTO,
    PlanVersionDTO,
)
from swe_ai_fleet.reports.ports.planning_read_port import PlanningReadPort


class ImplementationReportUseCase:
    def __init__(self, planning_store: PlanningReadPort) -> None:
        self.store = planning_store

    def generate(self, req: ReportRequest) -> Report:
        spec = self.store.get_case_spec(req.case_id)
        plan = self.store.get_plan_draft(req.case_id)
        events = (
            self.store.get_planning_events(req.case_id, count=req.max_events)
            if req.include_timeline
            else []
        )

        if not spec:
            raise ValueError("Case spec not found.")
        if not plan:
            raise ValueError("Plan draft not found.")

        md = self._render_markdown(spec, plan, events, req)
        stats = self._compute_stats(plan, events)
        report = Report(
            case_id=spec.case_id,
            plan_id=plan.plan_id,
            generated_at_ms=int(time.time() * 1000),
            markdown=md,
            stats=stats,
        )

        if req.persist_to_redis:
            self.store.save_report(spec.case_id, report, req.ttl_seconds)

        return report

    # ---- helpers ----

    @staticmethod
    def _compute_stats(plan: PlanVersionDTO, events: list[PlanningEventDTO]) -> dict[str, Any]:
        role_counts: dict[str, int] = {}
        deps_count = 0
        for s in plan.subtasks:
            role_counts[s.role] = role_counts.get(s.role, 0) + 1
            deps_count += len(s.depends_on or [])
        return {
            "total_subtasks": len(plan.subtasks),
            "dependencies": deps_count,
            "roles": role_counts,
            "events": len(events),
        }

    def _render_markdown(
        self,
        spec: CaseSpecDTO,
        plan: PlanVersionDTO,
        events: list[PlanningEventDTO],
        req: ReportRequest,
    ) -> str:
        lines: list[str] = []
        lines.append(f"# Implementation Report — {spec.title}\n")
        lines.append(f"- **Case ID:** `{spec.case_id}`")
        lines.append(f"- **Plan ID:** `{plan.plan_id}`")
        lines.append(f"- **Plan Status:** `{plan.status}`  |  " f"**Version:** `{plan.version}`")
        lines.append(
            f"- **Author:** `{plan.author_id}`  |  "
            f"**Generated at:** `{time.strftime('%Y-%m-%d %H:%M:%S')}`\n"
        )

        lines.append("## Overview")
        lines.append(spec.description or "_No description provided._")
        if req.include_constraints and spec.constraints:
            lines.append("\n### Constraints")
            for k, v in spec.constraints.items():
                lines.append(f"- **{k}:** {v}")
        if spec.tags:
            lines.append("\n### Tags")
            lines.append(", ".join(f"`{t}`" for t in spec.tags))

        if req.include_acceptance and spec.acceptance_criteria:
            lines.append("\n## Acceptance Criteria")
            for i, ac in enumerate(spec.acceptance_criteria, start=1):
                lines.append(f"{i}. {ac}")

        lines.append("\n## Plan Summary")
        lines.append(plan.rationale or "_No rationale provided._")

        lines.append("\n## Subtasks")
        if not plan.subtasks:
            lines.append("_No subtasks defined._")
        else:
            lines.append(
                "| ID | Title | Role | Depends On | Est. Points | Priority | Risk | Tech |"
            )
            lines.append("|---|---|---|---|---:|---:|---:|---|")
            for s in plan.subtasks:
                deps = ", ".join(s.depends_on) if s.depends_on else "-"
                tech = ", ".join(s.suggested_tech) if s.suggested_tech else "-"
                lines.append(
                    f"| `{s.subtask_id}` | {s.title} | `{s.role}` | {deps} | "
                    f"{s.estimate_points:.1f} | "
                    f"{s.priority} | {s.risk_score:.2f} | {tech} |"
                )

        if req.include_dependencies and plan.subtasks:
            lines.append("\n### Dependency Graph (Adjacency)")
            for s in plan.subtasks:
                deps = ", ".join(f"`{d}`" for d in (s.depends_on or [])) or "∅"
                lines.append(f"- `{s.subtask_id}` → {deps}")

        if req.include_timeline and events:
            lines.append("\n## Planning Timeline")
            for ev in events:
                ts_h = (
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ev.ts_ms / 1000))
                    if ev.ts_ms
                    else "-"
                )
                payload_preview = ""
                if ev.payload:
                    # compact preview (key:val limited)
                    items = list(ev.payload.items())[:4]
                    payload_preview = " | " + "; ".join(f"{k}={v}" for k, v in items)
                lines.append(f"- `{ts_h}` — **{ev.event}** by `{ev.actor}`{payload_preview}")

        lines.append("\n## Next Steps")
        lines.append("- Validate estimates and priorities with the human PO.")
        lines.append("- Gate approvals before execution (architecture and security reviews).")
        lines.append("- Prepare CI/CD and observability baselines for the involved services.")
        lines.append("")

        return "\n".join(lines)
