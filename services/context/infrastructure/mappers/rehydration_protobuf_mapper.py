"""Mapper from RehydrationBundle to protobuf responses.

Infrastructure layer mapper for gRPC response serialization.
"""

from typing import Any

from services.context.gen import context_pb2


class RehydrationProtobufMapper:
    """Mapper that converts RehydrationBundle to protobuf responses.
    
    Responsibility:
    - Domain bundle (dict-based) → Protobuf response
    - Handle all field mappings
    - Provide defaults for missing fields
    
    This is infrastructure-level serialization logic.
    Should NOT be in the server/servicer.
    """

    @staticmethod
    def bundle_to_response(bundle: Any) -> context_pb2.RehydrateSessionResponse:
        """Convert RehydrationBundle to protobuf response.
        
        Args:
            bundle: RehydrationBundle from application layer
            
        Returns:
            Protobuf RehydrateSessionResponse
        """
        packs = {}
        for role, pack in bundle.packs.items():
            packs[role] = RehydrationProtobufMapper._pack_to_proto(pack)

        return context_pb2.RehydrateSessionResponse(
            case_id=bundle.case_id,
            generated_at_ms=bundle.generated_at_ms,
            packs=packs,
            stats=context_pb2.RehydrationStats(
                decisions=bundle.stats.get("decisions", 0),
                decision_edges=bundle.stats.get("decision_edges", 0),
                impacts=bundle.stats.get("impacts", 0),
                events=bundle.stats.get("events", 0),
                roles=bundle.stats.get("roles", []),
            ),
        )

    @staticmethod
    def _pack_to_proto(pack: Any) -> context_pb2.RoleContextPack:
        """Convert RoleContextPack to protobuf.
        
        Args:
            pack: RoleContextPack from application layer
            
        Returns:
            Protobuf RoleContextPack
        """
        case_header = pack.case_header

        return context_pb2.RoleContextPack(
            role=pack.role,
            case_header=context_pb2.CaseHeader(
                case_id=case_header.get("case_id", ""),
                title=case_header.get("title", ""),
                description=case_header.get("description", ""),
                status="DRAFT",  # Default status, not in domain model
                created_at=case_header.get("created_at", ""),
                created_by=case_header.get("requester_id", ""),
            ),
            plan_header=context_pb2.PlanHeader(
                plan_id=pack.plan_header.get("plan_id", ""),
                version=pack.plan_header.get("version", 0),
                status=pack.plan_header.get("status", ""),
                total_subtasks=pack.plan_header.get("total_subtasks", 0),
                completed_subtasks=pack.plan_header.get("completed_subtasks", 0),
            ),
            subtasks=[
                RehydrationProtobufMapper._subtask_to_proto(st)
                for st in pack.role_subtasks
            ],
            decisions=[
                RehydrationProtobufMapper._decision_to_proto(d)
                for d in pack.decisions_relevant
            ],
            decision_deps=[
                RehydrationProtobufMapper._decision_relation_to_proto(dr)
                for dr in pack.decision_dependencies
            ],
            impacted=[
                RehydrationProtobufMapper._impacted_subtask_to_proto(imp)
                for imp in pack.impacted_subtasks
            ],
            milestones=[
                RehydrationProtobufMapper._milestone_to_proto(m)
                for m in pack.recent_milestones
            ],
            last_summary=pack.last_summary or "",
            token_budget_hint=pack.token_budget_hint,
        )

    @staticmethod
    def _subtask_to_proto(subtask: dict[str, Any]) -> context_pb2.Subtask:
        """Convert subtask dict to protobuf."""
        return context_pb2.Subtask(
            subtask_id=subtask.get("subtask_id", ""),
            title=subtask.get("title", ""),
            description=subtask.get("description", ""),
            role=subtask.get("role", ""),
            status=subtask.get("status", ""),
            dependencies=subtask.get("dependencies", []),
            priority=subtask.get("priority", 0),
        )

    @staticmethod
    def _decision_to_proto(decision: dict[str, Any]) -> context_pb2.Decision:
        """Convert decision dict to protobuf."""
        return context_pb2.Decision(
            id=decision.get("id", ""),
            title=decision.get("title", ""),
            rationale=decision.get("rationale", ""),
            status=decision.get("status", ""),
            decided_by=decision.get("decided_by", ""),
            decided_at=decision.get("decided_at", ""),
        )

    @staticmethod
    def _decision_relation_to_proto(relation: dict[str, Any]) -> context_pb2.DecisionRelation:
        """Convert decision relation dict to protobuf."""
        return context_pb2.DecisionRelation(
            src_id=relation.get("src_id", ""),
            dst_id=relation.get("dst_id", ""),
            relation_type=relation.get("relation_type", ""),
        )

    @staticmethod
    def _impacted_subtask_to_proto(impacted: dict[str, Any]) -> context_pb2.ImpactedSubtask:
        """Convert impacted subtask dict to protobuf."""
        return context_pb2.ImpactedSubtask(
            decision_id=impacted.get("decision_id", ""),
            subtask_id=impacted.get("subtask_id", ""),
            title=impacted.get("title", ""),
        )

    @staticmethod
    def _milestone_to_proto(milestone: dict[str, Any]) -> context_pb2.Milestone:
        """Convert milestone dict to protobuf."""
        return context_pb2.Milestone(
            event_type=milestone.get("event_type", ""),
            description=milestone.get("description", ""),
            ts_ms=milestone.get("ts_ms", 0),
            actor=milestone.get("actor", ""),
        )

