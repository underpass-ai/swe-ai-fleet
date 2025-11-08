"""Session rehydration use case.

Builds per-role context packs to resume work where it left off.
The decision graph (Neo4j) is the guiding source for decisions and impacts,
while Redis provides case specifications, draft plans, and planning
milestones/summaries.
"""

from __future__ import annotations

import time
from typing import Any

from core.reports.domain.decision_edges import DecisionEdges
from core.reports.domain.decision_node import DecisionNode
from core.reports.domain.task_node import TaskNode

from .domain.decision_relation_list import DecisionRelationList
from .domain.milestone_list import MilestoneList
from .domain.plan_header import PlanHeader
from .domain.rehydration_bundle import RehydrationBundle
from .domain.rehydration_request import RehydrationRequest
from .domain.role import Role
from .domain.role_context_fields import RoleContextFields
from .domain.task_plan import TaskPlan
from .domain.value_objects.rehydration_stats import RehydrationStats
from .infrastructure.mappers.rehydration_bundle_mapper import RehydrationBundleMapper
from .infrastructure.mappers.story_header_mapper import StoryHeaderMapper
from .ports.decisiongraph_read_port import DecisionGraphReadPort
from .ports.planning_read_port import PlanningReadPort

# --- module constants ---
DEFAULT_DECISION_FALLBACK_COUNT = 5
MILESTONE_EVENTS = {
    "create_case_spec",
    "propose_plan",
    "human_edit",
    "approve_plan",
}

TOKEN_BASE_ARCHITECT = 8192
TOKEN_BASE_DEFAULT = 4096
TOKEN_BUMP_PER_SUBTASK = 256
TOKEN_BUMP_PER_DECISION = 128
TOKEN_BUMP_MAX = 4096


class SessionRehydrationUseCase:
    """Build per-role context packs to resume an in-flight Story (formerly Case).

    Note: This use case reads from both the decision graph (truth for
    decisions/impacts) and the planning store (story spec, draft plan, and
    milestones/summaries). It does not mutate external state unless
    explicitly requested via the `persist_handoff_bundle` flag in the
    request.
    """

    def __init__(
        self,
        planning_store: PlanningReadPort,
        graph_store: DecisionGraphReadPort,
    ) -> None:
        self.plan_store = planning_store
        self.graph = graph_store

    def build(self, req: RehydrationRequest) -> RehydrationBundle:
        """Assemble a `RehydrationBundle` for the requested roles and Story (formerly Case).

        Raises:
            ValueError: If the story spec cannot be found.
        """
        spec = self.plan_store.get_case_spec(req.case_id)
        if not spec:
            raise ValueError("Story spec not found.")

        # Read from the graph (source of truth for decisions and impacts)
        graph_plan = self.graph.get_plan_by_case(req.case_id)
        decisions = self.graph.list_decisions(req.case_id)
        decision_dependency_edges = self.graph.list_decision_dependencies(req.case_id)
        decision_impacts = self.graph.list_decision_impacts(req.case_id)

        # Read from the planning store (draft plan, events, optional summary)
        redis_plan = self.plan_store.get_plan_draft(req.case_id)
        events = (
            self.plan_store.get_planning_events(req.case_id, count=req.timeline_events)
            if req.include_timeline
            else []
        )

        # Pre-index for fast assembly
        subtasks_by_role = _index_subtasks_by_role(redis_plan)
        decisions_by_id: dict[str, DecisionNode] = {d.id: d for d in decisions}
        dependencies_by_source = _index_decision_dependencies(decision_dependency_edges)
        impacts_by_decision = _index_impacts(decision_impacts)

        # Common headers (use mappers for conversion)
        story_header_obj = StoryHeaderMapper.from_spec(spec)
        story_header = StoryHeaderMapper.to_dict(story_header_obj)
        plan_header = PlanHeader.from_sources(graph_plan, redis_plan).to_dict()

        packs: dict[Role, RoleContextFields] = {}
        for role_str in req.roles:
            # Convert string to Role enum (fail-fast if invalid)
            try:
                role_enum = Role(role_str)
            except ValueError as e:
                raise ValueError(
                    f"Invalid role '{role_str}' in rehydration request. "
                    f"Valid roles: {', '.join(r.value for r in Role)}"
                ) from e

            role_subtasks = subtasks_by_role.get(role_str, [])
            relevant_decisions = _select_relevant_decisions(
                role_subtasks,
                impacts_by_decision,
                decisions_by_id,
                decisions,
            )

            decision_relations = DecisionRelationList.build(
                relevant_decisions, dependencies_by_source
            ).to_dicts()

            impacted_subtasks_for_role = _impacts_for_role(relevant_decisions, impacts_by_decision, role_str)

            milestones = MilestoneList.build_from_events(events, MILESTONE_EVENTS).to_sorted_dicts()

            # Optional last summary snapshot
            last_summary = None
            if req.include_summaries:
                last_summary = self.plan_store.read_last_summary(req.case_id)

            packs[role_enum] = RoleContextFields(
                role=role_str,  # RoleContextFields still uses string internally
                case_header=story_header,  # TODO: Rename field in RoleContextFields to story_header
                plan_header=plan_header,
                role_subtasks=[s.to_dict() for s in role_subtasks],
                decisions_relevant=[d.to_dict() for d in relevant_decisions],
                decision_dependencies=decision_relations,
                impacted_subtasks=impacted_subtasks_for_role,
                recent_milestones=sorted(milestones, key=lambda milestone: milestone["ts_ms"]),
                last_summary=last_summary,
                token_budget_hint=_suggest_token_budget(role_str, len(role_subtasks), len(relevant_decisions)),
            )

        # Create RehydrationStats value object
        stats = RehydrationStats(
            decisions_count=len(decisions),
            decision_edges_count=len(decision_dependency_edges),
            impacts_count=len(decision_impacts),
            events_count=len(events),
            roles=tuple(req.roles),
        )

        bundle = RehydrationBundle(
            story_id=spec.story_id,  # spec.story_id is StoryId
            generated_at_ms=int(time.time() * 1000),
            packs=packs,
            stats=stats,
        )

        if req.persist_handoff_bundle and hasattr(self.plan_store, "save_handoff_bundle"):
            # Use mapper to serialize bundle for persistence
            bundle_dict = RehydrationBundleMapper.to_dict(bundle)
            self.plan_store.save_handoff_bundle(req.case_id, bundle_dict, req.ttl_seconds)

        return bundle


# --- helpers ---


def _index_subtasks_by_role(
    plan: Any | None,
) -> dict[str, list[TaskPlan]]:
    """Group plan tasks by role for quick lookup (formerly subtasks).

    Accepts `None` and returns an empty mapping.
    """
    subtasks_by_role: dict[str, list[TaskPlan]] = {}
    if plan:
        for subtask in plan.subtasks:
            subtasks_by_role.setdefault(subtask.role, []).append(subtask)
    return subtasks_by_role


def _index_decision_dependencies(
    edges: list[DecisionEdges],
) -> dict[str, list[DecisionEdges]]:
    """Index decision dependency edges by their source decision id."""
    dependencies_by_source: dict[str, list[DecisionEdges]] = {}
    for edge in edges:
        dependencies_by_source.setdefault(edge.src_id, []).append(edge)
    return dependencies_by_source


def _index_impacts(
    impacts: list[tuple[str, TaskNode]],
) -> dict[str, list[TaskNode]]:
    """Index task impacts by decision id (formerly subtask impacts)."""
    impacts_by_decision: dict[str, list[TaskNode]] = {}
    for decision_id, task_node in impacts:
        impacts_by_decision.setdefault(decision_id, []).append(task_node)
    return impacts_by_decision


def _select_relevant_decisions(
    role_subtasks: list[TaskPlan],
    impacts_by_decision: dict[str, list[TaskNode]],
    decisions_by_id: dict[str, DecisionNode],
    all_decisions: list[DecisionNode],
) -> list[DecisionNode]:
    """Select decisions relevant to a role's tasks (formerly subtasks).

    If no decisions are found via impact links, fall back to the first
    DEFAULT_DECISION_FALLBACK_COUNT ordered decisions to maintain guidance.
    """
    relevant: list[DecisionNode] = []
    if role_subtasks:
        subtask_ids = {subtask.subtask_id for subtask in role_subtasks}
        for decision_id, impacted_subtasks in impacts_by_decision.items():
            if any(subtask.id in subtask_ids for subtask in impacted_subtasks):
                decision = decisions_by_id.get(decision_id)
                if decision:
                    relevant.append(decision)

    if not relevant:
        return all_decisions[:DEFAULT_DECISION_FALLBACK_COUNT]
    return relevant


def _impacts_for_role(
    relevant_decisions: list[DecisionNode],
    impacts_by_decision: dict[str, list[TaskNode]],
    role: str,
) -> list[dict[str, Any]]:
    """Filter impacted tasks for `role` across the relevant decisions (formerly subtasks)."""
    impacted: list[dict[str, Any]] = []
    for decision in relevant_decisions:
        for task_node in impacts_by_decision.get(decision.id, []):
            if task_node.role == role:
                impacted.append(
                    {
                        "decision_id": decision.id,
                        "subtask_id": task_node.id,  # Legacy key name
                        "title": task_node.title,
                    }
                )
    return impacted


def _suggest_token_budget(role: str, sub_count: int, dec_count: int) -> int:
    """Suggest a token budget using a simple, tunable heuristic."""
    base = TOKEN_BASE_ARCHITECT if role == "architect" else TOKEN_BASE_DEFAULT
    bump = min(
        TOKEN_BUMP_MAX,
        sub_count * TOKEN_BUMP_PER_SUBTASK + dec_count * TOKEN_BUMP_PER_DECISION,
    )
    return base + bump
