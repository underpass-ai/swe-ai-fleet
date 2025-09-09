from __future__ import annotations

import time
from typing import Any

from swe_ai_fleet.reports.adapters.redis_planning_read_adapter import (
    RedisPlanningReadAdapter,
)
from swe_ai_fleet.reports.domain.decision_edges import DecisionEdges
from swe_ai_fleet.reports.domain.decision_enriched_report import (
    DecisionEnrichedReport,
)
from swe_ai_fleet.reports.domain.decision_node import DecisionNode
from swe_ai_fleet.reports.domain.report import Report
from swe_ai_fleet.reports.domain.report_request import ReportRequest
from swe_ai_fleet.reports.domain.subtask_node import SubtaskNode
from swe_ai_fleet.reports.dtos.dtos import (
    CaseSpecDTO,
    PlanningEventDTO,
    PlanVersionDTO,
)
from swe_ai_fleet.reports.ports.decision_graph_read_port import (
    DecisionGraphReadPort,
)


class DecisionEnrichedReportUseCase:
    """
    Generates a Markdown report guided by the decision graph (Neo4j),
    and enriched with planning milestones (Redis).
    """

    def __init__(
        self,
        redis_store: RedisPlanningReadAdapter,
        graph_store: DecisionGraphReadPort,
    ) -> None:
        self.redis = redis_store
        self.graph = graph_store

    def generate(self, req: ReportRequest) -> DecisionEnrichedReport:
        spec = self.redis.get_case_spec(req.case_id)
        if not spec:
            raise ValueError("Case spec not found.")

        # Graph-driven core
        plan_g = self.graph.get_plan_by_case(req.case_id)
        decisions = self.graph.list_decisions(req.case_id)
        dep_edges = self.graph.list_decision_dependencies(req.case_id)
        impacts = self.graph.list_decision_impacts(req.case_id)

        # Redis-driven milestones / timeline
        events = (
            self.redis.get_planning_events(req.case_id, count=req.max_events) if req.include_timeline else []
        )
        plan_r = self.redis.get_plan_draft(req.case_id)  # to get subtasks table if you want to display it

        md = self._render_markdown(
            spec,
            plan_g or plan_r,
            decisions,
            dep_edges,
            impacts,
            events,
            req,
        )
        stats = self._compute_stats(
            decisions,
            dep_edges,
            impacts,
            plan_g or plan_r,
            events,
        )
        report = DecisionEnrichedReport(
            case_id=spec.case_id,
            plan_id=(plan_g.plan_id if plan_g else (plan_r.plan_id if plan_r else None)),
            generated_at_ms=int(time.time() * 1000),
            markdown=md,
            stats=stats,
        )

        if req.persist_to_redis:
            # re-use implementation report storage keys to avoid proliferation
            ir = Report(
                case_id=report.case_id,
                plan_id=report.plan_id,
                generated_at_ms=report.generated_at_ms,
                markdown=report.markdown,
                stats=report.stats,
            )
            self.redis.save_report(spec.case_id, ir, req.ttl_seconds)

        return report

    # ---- helpers ----

    @staticmethod
    def _compute_stats(
        decisions: list[DecisionNode],
        dep_edges: list[DecisionEdges],
        impacts: list[tuple[str, SubtaskNode]],
        plan: PlanVersionDTO | None,
        events: list[PlanningEventDTO],
    ) -> dict[str, Any]:
        deps_per_decision: dict[str, int] = {}
        for e in dep_edges:
            deps_per_decision[e.src_id] = deps_per_decision.get(e.src_id, 0) + 1
        impact_counts: dict[str, int] = {}
        for did, _ in impacts:
            impact_counts[did] = impact_counts.get(did, 0) + 1
        return {
            "decisions": len(decisions),
            "decision_edges": len(dep_edges),
            "impacted_subtasks": len(impacts),
            "plan_status": (plan.status if plan else "UNKNOWN"),
            "events": len(events),
            "max_dependencies_on_one_decision": (max(deps_per_decision.values()) if deps_per_decision else 0),
            "max_impacts_from_one_decision": (max(impact_counts.values()) if impact_counts else 0),
        }

    def _render_markdown(
        self,
        spec: CaseSpecDTO,
        plan: PlanVersionDTO | None,
        decisions: list[DecisionNode],
        dep_edges: list[DecisionEdges],
        impacts: list[tuple[str, SubtaskNode]],
        events: list[PlanningEventDTO],
        req: ReportRequest,
    ) -> str:
        def fmt_ts(ms: int) -> str:
            if not ms:
                return "-"
            return time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(ms / 1000),
            )

        lines: list[str] = []
        lines.append(f"# Implementation Report (Graph-guided) — {spec.title}\n")
        lines.append(f"- **Case ID:** `{spec.case_id}`")
        if plan:
            lines.append(
                f"- **Plan ID:** `{plan.plan_id}`  |  "
                f"**Status:** `{plan.status}`  |  "
                f"**Version:** `{plan.version}`"
            )
        lines.append(f"- **Generated at:** `{time.strftime('%Y-%m-%d %H:%M:%S')}`\n")

        lines.append("## Overview")
        lines.append(spec.description or "_No description provided._")
        if req.include_constraints and spec.constraints:
            lines.append("\n### Constraints")
            for k, v in spec.constraints.items():
                lines.append(f"- **{k}:** {v}")
        if spec.acceptance_criteria and req.include_acceptance:
            lines.append("\n### Acceptance Criteria")
            for i, ac in enumerate(spec.acceptance_criteria, start=1):
                lines.append(f"{i}. {ac}")

        # ----- Graph: Decisions -----
        lines.append("\n## Decisions (ordered)")
        if not decisions:
            lines.append("_No decisions projected in graph._")
        else:
            lines.append("| ID | Title | Status | Author | Created At |")
            lines.append("|---|---|---|---|---|")
            for d in decisions:
                lines.append(
                    f"| `{d.id}` | {d.title} | `{d.status}` | `{d.author_id}` | {fmt_ts(d.created_at_ms)} |"
                )

        # ----- Graph: Dependencies between decisions -----
        lines.append("\n## Decision Dependency Map")
        if not dep_edges:
            lines.append("_No dependencies between decisions._")
        else:
            # adjacency-like compact view
            by_src: dict[str, list[DecisionEdges]] = {}
            for e in dep_edges:
                by_src.setdefault(e.src_id, []).append(e)
            for src, edges in by_src.items():
                rhs = ", ".join(f"`{e.rel_type}` → `{e.dst_id}`" for e in edges)
                lines.append(f"- `{src}`: {rhs}")

        # ----- Graph: Impacts on Subtasks -----
        lines.append("\n## Decision → Subtask Impact")
        if not impacts:
            lines.append("_No subtask influenced by decisions._")
        else:
            lines.append("| Decision | Subtask | Role |")
            lines.append("|---|---|---|")
            for did, s in impacts:
                lines.append(f"| `{did}` | `{s.id}`: {s.title} | `{s.role}` |")

        # ----- (Optional) Subtasks table from Redis draft -----
        if plan and req.include_dependencies:
            # Try to enrich from Redis draft subtasks if available
            draft = self.redis.get_plan_draft(spec.case_id)
            if draft and draft.subtasks:
                lines.append("\n## Subtasks (from planning draft)")
                lines.append("| ID | Title | Role | Depends On | Est. Points | Priority | Risk | Tech |")
                lines.append("|---|---|---|---|---:|---:|---:|---|")
                for st in draft.subtasks:
                    deps = ", ".join(st.depends_on) if st.depends_on else "-"
                    tech = ", ".join(st.suggested_tech) if st.suggested_tech else "-"
                    lines.append(
                        f"| `{st.subtask_id}` | {st.title} | `{st.role}` | "
                        f"{deps} | {st.estimate_points:.1f} | "
                        f"{st.priority} | {st.risk_score:.2f} | {tech} |"
                    )

        # ----- Milestones (PO-led) from Redis planning events -----
        if req.include_timeline and events:
            lines.append("\n## Milestones & Timeline (PO-led)")
            # Extract key milestones
            milestones: list[str] = []
            for ev in events:
                ts = fmt_ts(ev.ts_ms)
                if ev.event == "create_case_spec":
                    milestones.append(f"- `{ts}` — **Case created** by `{ev.actor}`")
                elif ev.event == "propose_plan":
                    milestones.append(f"- `{ts}` — **Plan proposed** by `{ev.actor}`")
                elif ev.event == "human_edit":
                    milestones.append(f"- `{ts}` — **Human edits** by `{ev.actor}`")
                elif ev.event == "approve_plan":
                    milestones.append(f"- `{ts}` — **Plan approved** by `{ev.actor}` ✅")
            if plan:
                milestones.append(f"- **Current plan status:** `{plan.status}` (v{plan.version})")
            lines.extend(milestones or ["_No milestones found._"])

        # ----- Next steps -----
        lines.append("\n## Next Steps")
        lines.append("- Validate decision dependencies vs. implementation order.")
        lines.append("- Ensure observability and security decisions are reflected in CI/CD.")
        lines.append("- Reconcile plan status with PO priorities and delivery timeline.")
        lines.append("")
        return "\n".join(lines)
