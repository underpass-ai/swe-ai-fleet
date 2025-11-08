"""Session Rehydration Application Service.

This Application Service orchestrates the rehydration process,
coordinating between multiple ports and domain logic.
"""

import time
from dataclasses import dataclass

from core.context.domain.decision_relation_list import DecisionRelationList
from core.context.domain.entity_ids.decision_id import DecisionId
from core.context.domain.graph_relation_type import GraphRelationType
from core.context.domain.milestone_event_type import MilestoneEventType
from core.context.domain.milestone_list import MilestoneList
from core.context.domain.plan_header import PlanHeader
from core.context.domain.rehydration_bundle import RehydrationBundle
from core.context.domain.rehydration_request import RehydrationRequest
from core.context.domain.role import Role
from core.context.domain.role_context_fields import RoleContextFields
from core.context.domain.services.data_indexer import DataIndexer
from core.context.domain.services.decision_selector import DecisionSelector
from core.context.domain.services.impact_calculator import ImpactCalculator

# Import domain services (to be created)
from core.context.domain.services.token_budget_calculator import TokenBudgetCalculator
from core.context.domain.story_header import StoryHeader
from core.context.domain.value_objects.decision_relation import DecisionRelation
from core.context.domain.value_objects.impacted_task import ImpactedTask
from core.context.domain.value_objects.indexed_story_data import IndexedStoryData
from core.context.domain.value_objects.milestone import Milestone
from core.context.domain.value_objects.rehydration_stats import RehydrationStats
from core.context.infrastructure.mappers.rehydration_bundle_mapper import RehydrationBundleMapper
from core.context.infrastructure.mappers.story_header_mapper import StoryHeaderMapper
from core.context.infrastructure.mappers.story_mapper import StoryMapper
from core.context.ports.decisiongraph_read_port import DecisionGraphReadPort
from core.context.ports.planning_read_port import PlanningReadPort


@dataclass
class SessionRehydrationApplicationService:
    """Application Service for session rehydration.

    This service orchestrates the process of building context bundles for agents.
    It coordinates between:
    - Planning data (Redis/Valkey)
    - Decision graph (Neo4j)
    - Domain services (pure logic)
    - Infrastructure mappers

    Following Hexagonal Architecture:
    - Receives ports via constructor (Dependency Injection)
    - Delegates domain logic to domain services
    - Uses mappers for data transformation
    - Returns domain aggregates (NO DTOs)
    """

    # Infrastructure ports (injected)
    planning_store: PlanningReadPort
    graph_store: DecisionGraphReadPort

    # Domain services (injected)
    token_calculator: TokenBudgetCalculator
    decision_selector: DecisionSelector
    impact_calculator: ImpactCalculator
    data_indexer: DataIndexer

    def rehydrate_session(self, req: RehydrationRequest) -> RehydrationBundle:
        """Build a complete RehydrationBundle for the requested story and roles.

        This is the main orchestration method that coordinates all steps.

        Args:
            req: Rehydration request with story_id and roles

        Returns:
            RehydrationBundle with context for all requested roles

        Raises:
            ValueError: If story not found or roles invalid
        """
        # Step 1: Fetch story specification (fail-fast if not found)
        spec = self.planning_store.get_case_spec(req.case_id)
        if not spec:
            raise ValueError(f"Story spec not found for case_id: {req.case_id}")

        # Step 2: Fetch all data sources in parallel (conceptually)
        graph_plan = self.graph_store.get_plan_by_case(req.case_id)
        decisions = self.graph_store.list_decisions(req.case_id)
        decision_dependency_edges = self.graph_store.list_decision_dependencies(req.case_id)
        decision_impacts = self.graph_store.list_decision_impacts(req.case_id)

        redis_plan = self.planning_store.get_plan_draft(req.case_id)
        events = (
            self.planning_store.get_planning_events(req.case_id, count=req.timeline_events)
            if req.include_timeline
            else []
        )

        # Step 3: Build Story entity from spec (use mapper)
        story = StoryMapper.from_spec(spec)

        # Step 3b: Fetch epic (REQUIRED - every story must have an epic)
        # The adapter will fail-fast if epic not found (domain invariant)
        epic = self.graph_store.get_epic_by_story(req.case_id)

        # Step 3c: Index data for fast lookups (domain service)
        indexed_data = self.data_indexer.index(
            epic=epic,  # REQUIRED (domain invariant)
            story=story,
            redis_plan=redis_plan,
            decisions=decisions,
            decision_dependencies=decision_dependency_edges,
            decision_impacts=decision_impacts,
        )

        # Step 4: Build common headers (domain entities, NOT dicts)
        story_header = StoryHeaderMapper.from_spec(spec)
        plan_header = PlanHeader.from_sources(graph_plan, redis_plan)

        # Step 5: Build context pack for each role
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

            # Build pack for this specific role
            pack = self._build_pack_for_role(
                role=role_enum,
                role_str=role_str,
                indexed_data=indexed_data,
                story_header=story_header,
                plan_header=plan_header,
                events=events,
                req=req,
            )
            packs[role_enum] = pack

        # Step 6: Compute statistics
        stats = RehydrationStats(
            decisions_count=len(decisions),
            decision_edges_count=len(decision_dependency_edges),
            impacts_count=len(decision_impacts),
            events_count=len(events),
            roles=tuple(req.roles),
        )

        # Step 7: Assemble final bundle
        bundle = RehydrationBundle(
            story_id=spec.story_id,
            generated_at_ms=int(time.time() * 1000),
            packs=packs,
            stats=stats,
        )

        # Step 8: Persist bundle if requested
        if req.persist_handoff_bundle:
            bundle_dict = RehydrationBundleMapper.to_dict(bundle)
            self.planning_store.save_handoff_bundle(
                req.case_id,
                bundle_dict,
                req.ttl_seconds
            )

        return bundle

    def _build_pack_for_role(
        self,
        role: Role,
        role_str: str,
        indexed_data: IndexedStoryData,
        story_header: StoryHeader,
        plan_header: PlanHeader,
        events: list,
        req: RehydrationRequest,
    ) -> RoleContextFields:
        """Build context pack for a single role (extracted method).

        Args:
            role: Role enum
            role_str: Role string (for legacy compatibility in indexing)
            indexed_data: Indexed story data
            story_header: StoryHeader domain entity
            plan_header: PlanHeader domain entity
            events: Planning events
            req: Original request

        Returns:
            RoleContextFields with domain entities (NO dicts)
        """
        # Get tasks for this role
        role_tasks = indexed_data.subtasks_by_role.get(role_str, [])

        # Select relevant decisions (domain service)
        relevant_decisions = self.decision_selector.select_for_role(
            role_tasks=role_tasks,
            impacts_by_decision=indexed_data.impacts_by_decision,
            decisions_by_id=indexed_data.decisions_by_id,
            all_decisions=indexed_data.all_decisions,
        )

        # Build decision relations (convert to Value Objects)
        decision_relations_raw = DecisionRelationList.build(
            relevant_decisions,
            indexed_data.dependencies_by_source
        ).to_dicts()

        # Convert to DecisionRelation Value Objects
        decision_relations = tuple(
            DecisionRelation(
                source_decision_id=DecisionId(value=rel["src_id"]),
                target_decision_id=DecisionId(value=rel["dst_id"]),
                relation_type=GraphRelationType(rel["rel_type"]),  # Convert string to enum
            )
            for rel in decision_relations_raw
        )

        # Calculate impacted tasks (domain service)
        impacted_tasks_raw = self.impact_calculator.calculate_for_role(
            relevant_decisions=relevant_decisions,
            impacts_by_decision=indexed_data.impacts_by_decision,
            role=role_str,
        )

        # Convert to ImpactedTask Value Objects
        impacted_tasks = tuple(
            ImpactedTask(
                decision_id=impact.decision_id,  # Already DecisionId VO
                task_id=impact.task_id,          # Already TaskId VO
                title=impact.title,
            )
            for impact in impacted_tasks_raw
        )

        # Build milestones (convert to Milestone Value Objects)
        milestone_events = MilestoneEventType.get_default_milestone_events()
        milestone_event_strings = {event.value for event in milestone_events}
        milestones_raw = MilestoneList.build_from_events(events, milestone_event_strings).to_sorted_dicts()

        # Convert to Milestone Value Objects
        milestones = tuple(
            Milestone(
                event_type=MilestoneEventType(m["event_type"]),
                timestamp_ms=m["ts_ms"],
                event_id=m.get("event_id", ""),
                metadata=m.get("metadata", ""),
            )
            for m in milestones_raw
        )

        # Get last summary if requested
        last_summary = None
        if req.include_summaries:
            last_summary = self.planning_store.read_last_summary(req.case_id)

        # Calculate token budget (domain service)
        token_budget = self.token_calculator.calculate(
            role=role,
            task_count=len(role_tasks),
            decision_count=len(relevant_decisions),
        )

        # Build RoleContextFields with domain entities and Value Objects (NO dicts)
        return RoleContextFields(
            role=role,  # Role enum
            story_header=story_header,  # StoryHeader entity
            plan_header=plan_header,  # PlanHeader entity
            role_tasks=tuple(role_tasks),  # Immutable tuple of TaskPlan entities
            decisions_relevant=relevant_decisions,  # list[DecisionNode]
            decision_dependencies=decision_relations,  # tuple[DecisionRelation, ...] VOs
            impacted_tasks=impacted_tasks,  # tuple[ImpactedTask, ...] VOs
            recent_milestones=milestones,  # tuple[Milestone, ...] VOs (already sorted)
            last_summary=last_summary,
            token_budget_hint=token_budget,
        )

