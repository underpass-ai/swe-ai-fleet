from __future__ import annotations

import time
from typing import Any

from swe_ai_fleet.reports.domain.decision_edges import DecisionEdges
from swe_ai_fleet.reports.domain.decision_node import DecisionNode
from swe_ai_fleet.reports.domain.subtask_node import SubtaskNode
from swe_ai_fleet.reports.dtos.dtos import SubtaskPlanDTO

from .domain.rehydration_bundle import RehydrationBundle
from .domain.rehydration_request import RehydrationRequest
from .domain.role_context_pack import RoleContextPack
from .ports.decisiongraph_read_port import DecisionGraphReadPort
from .ports.planning_read_port import PlanningReadPort


class SessionRehydrationUseCase:
    """
    Builds per-role context packs to resume work where it left off.
    Graph (Neo4j) is the guiding truth for decisions/impacts.
    Redis provides case spec, draft plan and planning milestones/summaries.
    """

    def __init__(
        self,
        planning_store: PlanningReadPort,
        graph_store: DecisionGraphReadPort,
    ) -> None:
        self.plan_store = planning_store
        self.graph = graph_store

    def build(self, req: RehydrationRequest) -> RehydrationBundle:
        spec = self.plan_store.get_case_spec(req.case_id)
        if not spec:
            raise ValueError("Case spec not found.")

        # Core from graph
        plan_g = self.graph.get_plan_by_case(req.case_id)
        decisions = self.graph.list_decisions(req.case_id)
        dep_edges = self.graph.list_decision_dependencies(req.case_id)
        impacts = self.graph.list_decision_impacts(req.case_id)

        # From Redis
        plan_r = self.plan_store.get_plan_draft(req.case_id)  # for subtasks by role
        events = (
            self.plan_store.get_planning_events(req.case_id, count=req.timeline_events)
            if req.include_timeline
            else []
        )

        # Pre-index for fast assembly
        subtasks_by_role: dict[str, list[SubtaskPlanDTO]] = {}
        if plan_r:
            for subtask in plan_r.subtasks:
                subtasks_by_role.setdefault(subtask.role, []).append(subtask)

        decisions_by_id: dict[str, DecisionNode] = {d.id: d for d in decisions}
        deps_by_src: dict[str, list[DecisionEdges]] = {}
        for e in dep_edges:
            deps_by_src.setdefault(e.src_id, []).append(e)

        impacts_by_decision: dict[str, list[SubtaskNode]] = {}
        for did, sub in impacts:
            impacts_by_decision.setdefault(did, []).append(sub)

        # Common headers
        case_header = {
            "case_id": spec.case_id,
            "title": spec.title,
            "constraints": spec.constraints,
            "acceptance_criteria": spec.acceptance_criteria,
            "tags": spec.tags,
        }
        plan_header = {
            "plan_id": (plan_g.plan_id if plan_g else (plan_r.plan_id if plan_r else "")),
            "status": (plan_g.status if plan_g else (plan_r.status if plan_r else "UNKNOWN")),
            "version": (plan_g.version if plan_g else (plan_r.version if plan_r else 0)),
            "rationale": (plan_g.rationale if plan_g else (plan_r.rationale if plan_r else "")),
        }

        packs: dict[str, Any] = {}
        for role in req.roles:
            role_subs = subtasks_by_role.get(role, [])
            # Decisions relevant: those that impact this role's subtasks OR
            # global core decisions (no impact edges present)
            relevant_decisions: list[DecisionNode] = []
            if role_subs:
                sub_ids = {s.subtask_id for s in role_subs}
                # decisions that influence any of these subtasks
                for did, subs in impacts_by_decision.items():
                    if any(sub.id in sub_ids for sub in subs):
                        d = decisions_by_id.get(did)
                        if d:
                            relevant_decisions.append(d)

            # if none found, fall back to first N ordered decisions to
            # maintain minimum guidance
            if not relevant_decisions:
                relevant_decisions = decisions[:5]

            # Build dependency slice for those decisions
            dep_slice: list[DecisionEdges] = []
            rel_set: list[dict[str, Any]] = []
            seen = set()
            for d in relevant_decisions:
                for e in deps_by_src.get(d.id, []):
                    dep_slice.append(e)
                    rel_set.append({"src": e.src_id, "rel": e.rel_type, "dst": e.dst_id})
                    seen.add((e.src_id, e.rel_type, e.dst_id))

            # Impacts for relevant decisions limited to this role
            impacted_here: list[dict[str, Any]] = []
            for d in relevant_decisions:
                for subnode in impacts_by_decision.get(d.id, []):
                    if subnode.role == role:
                        impacted_here.append(
                            {
                                "decision_id": d.id,
                                "subtask_id": subnode.id,
                                "title": subnode.title,
                            }
                        )

            # Recent milestones (PO-led)
            milestones: list[dict[str, Any]] = []
            for ev in events:
                if ev.event in {
                    "create_case_spec",
                    "propose_plan",
                    "human_edit",
                    "approve_plan",
                }:
                    milestones.append(
                        {
                            "ts_ms": ev.ts_ms,
                            "event": ev.event,
                            "actor": ev.actor,
                        }
                    )

            # Optional last summary snapshot
            last_summary = None
            if req.include_summaries and hasattr(self.plan_store, "read_last_summary"):
                last_summary = self.plan_store.read_last_summary(req.case_id)

            packs[role] = RoleContextPack(
                role=role,
                case_header=case_header,
                plan_header=plan_header,
                role_subtasks=[_st_to_dict(s) for s in role_subs],
                decisions_relevant=[_dec_to_dict(d) for d in relevant_decisions],
                decision_dependencies=rel_set,
                impacted_subtasks=impacted_here,
                recent_milestones=sorted(milestones, key=lambda milestone: milestone["ts_ms"]),
                last_summary=last_summary,
                token_budget_hint=_suggest_token_budget(role, len(role_subs), len(relevant_decisions)),
            )

        bundle = RehydrationBundle(
            case_id=spec.case_id,
            generated_at_ms=int(time.time() * 1000),
            packs=packs,
            stats={
                "decisions": len(decisions),
                "decision_edges": len(dep_edges),
                "impacts": len(impacts),
                "events": len(events),
                "roles": req.roles,
            },
        )

        if req.persist_handoff_bundle and hasattr(self.plan_store, "save_handoff_bundle"):
            self.plan_store.save_handoff_bundle(req.case_id, _bundle_to_dict(bundle), req.ttl_seconds)

        return bundle


# --- helpers ---


def _st_to_dict(s: SubtaskPlanDTO) -> dict[str, Any]:
    return {
        "subtask_id": s.subtask_id,
        "title": s.title,
        "description": s.description,
        "role": s.role,
        "depends_on": list(s.depends_on or []),
        "estimate_points": float(s.estimate_points),
        "priority": int(s.priority),
        "risk_score": float(s.risk_score),
        "suggested_tech": list(s.suggested_tech or []),
        "notes": s.notes,
    }


def _dec_to_dict(d: DecisionNode) -> dict[str, Any]:
    return {
        "id": d.id,
        "title": d.title,
        "rationale": d.rationale,
        "status": d.status,
        "author_id": d.author_id,
        "created_at_ms": d.created_at_ms,
    }


def _suggest_token_budget(role: str, sub_count: int, dec_count: int) -> int:
    # simple heuristic that can be tuned per model
    base = 8192 if role == "architect" else 4096
    bump = min(4096, sub_count * 256 + dec_count * 128)
    return base + bump


def _bundle_to_dict(b: RehydrationBundle) -> dict[str, Any]:
    return {
        "case_id": b.case_id,
        "generated_at_ms": b.generated_at_ms,
        "packs": {
            role: {
                "role": p.role,
                "case_header": p.case_header,
                "plan_header": p.plan_header,
                "role_subtasks": p.role_subtasks,
                "decisions_relevant": p.decisions_relevant,
                "decision_dependencies": p.decision_dependencies,
                "impacted_subtasks": p.impacted_subtasks,
                "recent_milestones": p.recent_milestones,
                "last_summary": p.last_summary,
                "token_budget_hint": p.token_budget_hint,
            }
            for role, p in b.packs.items()
        },
        "stats": b.stats,
    }
