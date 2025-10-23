from __future__ import annotations

import time
from typing import Any

from core.reports.domain.report import Report
from core.reports.domain.report_request import ReportRequest
from core.reports.dtos.dtos import (
    CaseSpecDTO,
    PlanningEventDTO,
    PlanVersionDTO,
)
from core.reports.ports.planning_read_port import PlanningReadPort

try:
    from core.reports.ports.graph_analytics_read_port import GraphAnalyticsReadPort
except Exception:  # keep optional import to avoid breaking environments without the new port
    GraphAnalyticsReadPort = object  # type: ignore


class ImplementationReportUseCase:
    def __init__(
        self,
        planning_store: PlanningReadPort,
        analytics_port: GraphAnalyticsReadPort | None = None,
    ) -> None:
        self.store = planning_store
        self.analytics_port = analytics_port

    def generate(self, req: ReportRequest) -> Report:
        spec = self.store.get_case_spec(req.case_id)
        plan = self.store.get_plan_draft(req.case_id)
        events = (
            self.store.get_planning_events(req.case_id, count=req.max_events) if req.include_timeline else []
        )

        if not spec:
            raise ValueError("Case spec not found.")
        if not plan:
            raise ValueError("Plan draft not found.")

        md = self._render_markdown(spec, plan, events, req)
        if self.analytics_port is not None:
            md += "\n\n" + self._render_analytics(spec.case_id)
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
        lines.append(f"- **Plan Status:** `{plan.status}`  |  **Version:** `{plan.version}`")
        lines.append(
            f"- **Author:** `{plan.author_id}`  |  **Generated at:** `{time.strftime('%Y-%m-%d %H:%M:%S')}`\n"
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
            lines.append("| ID | Title | Role | Depends On | Est. Points | Priority | Risk | Tech |")
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
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ev.ts_ms / 1000)) if ev.ts_ms else "-"
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

    # --- new helper ---
    def _render_analytics(self, case_id: str) -> str:
        assert self.analytics_port is not None
        lines: list[str] = []
        lines.append("## Graph Analytics (Decisions)")
        # Critical
        crit = self.analytics_port.get_critical_decisions(case_id, limit=10)
        lines.append("### Critical Decisions (by indegree)")
        if not crit:
            lines.append("- (none)")
        else:
            for c in crit:
                lines.append(f"- `{c.id}` — score {c.score:.2f}")
        # Cycles
        cycles = self.analytics_port.find_cycles(case_id, max_depth=6)
        lines.append("\n### Cycles")
        if not cycles:
            lines.append("- (none)")
        else:
            for i, cy in enumerate(cycles, start=1):
                path_txt = " -> ".join(cy.nodes)
                lines.append(f"- Cycle {i}: {path_txt}")
        # Layers
        layers = self.analytics_port.topo_layers(case_id)
        lines.append("\n### Topological Layers")
        if not layers.layers:
            lines.append("- (none)")
        else:
            for i, layer in enumerate(layers.layers):
                if not layer:
                    continue
                lines.append(f"- Layer {i}: {', '.join(layer)}")
        return "\n".join(lines)
