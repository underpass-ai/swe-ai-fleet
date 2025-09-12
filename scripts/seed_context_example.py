#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict

from swe_ai_fleet.context.adapters.neo4j_command_store import (
    Neo4jCommandStore,
)
from swe_ai_fleet.context.adapters.neo4j_command_store import (
    Neo4jConfig as Neo4jCmdCfg,
)
from swe_ai_fleet.context.adapters.redis_planning_read_adapter import (
    RedisPlanningReadAdapter as ContextRedisAdapter,
)
from swe_ai_fleet.memory.redis_store import RedisStoreImpl
from swe_ai_fleet.reports.dtos.dtos import CaseSpecDTO, PlanVersionDTO, SubtaskPlanDTO


def seed_redis_example(case_id: str, url: str) -> None:
    r = RedisStoreImpl(url).client
    adapter = ContextRedisAdapter(r)

    now = int(time.time() * 1000)

    # 1) Case spec
    spec = CaseSpecDTO(
        case_id=case_id,
        title="Build minimal context demo",
        description="Seed Redis and Neo4j with a tiny example for the context bounded context.",
        acceptance_criteria=[
            "Redis contains case spec and plan draft",
            "Neo4j contains decisions and relations",
        ],
        requester_id="user:demo",
        tags=["demo", "context"],
        created_at_ms=now,
    )
    r.set(adapter._k_spec(case_id), json.dumps(asdict(spec)))

    # 2) Plan draft with two subtasks
    s1 = SubtaskPlanDTO(
        subtask_id="S1",
        title="Design Redis keys",
        description="Define and store case spec and plan draft",
        role="architect",
        suggested_tech=["redis"],
        estimate_points=1.0,
        priority=1,
    )
    s2 = SubtaskPlanDTO(
        subtask_id="S2",
        title="Model decisions in Neo4j",
        description="Create Decision nodes and relationships",
        role="developer",
        suggested_tech=["neo4j"],
        depends_on=["S1"],
        estimate_points=2.0,
        priority=2,
    )
    plan = PlanVersionDTO(
        plan_id=f"P-{case_id}",
        case_id=case_id,
        version=1,
        status="DRAFT",
        author_id="agent:planner",
        rationale="Demo plan for context seed",
        subtasks=[s1, s2],
        created_at_ms=now,
    )
    r.set(
        adapter._k_draft(case_id),
        json.dumps(
            {
                "plan_id": plan.plan_id,
                "case_id": plan.case_id,
                "version": plan.version,
                "status": plan.status,
                "author_id": plan.author_id,
                "rationale": plan.rationale,
                "subtasks": [s1.to_dict(), s2.to_dict()],
                "created_at_ms": plan.created_at_ms,
            }
        ),
    )

    # 3) Planning events stream (minimal)
    r.xadd(
        adapter._k_stream(case_id),
        {
            "event": "create_case_spec",
            "actor": "agent:planner",
            "payload": json.dumps({"case_id": case_id}),
            "ts": str(now),
        },
        maxlen=256,
        approximate=True,
    )


def seed_neo4j_example(case_id: str) -> None:
    cfg = Neo4jCmdCfg(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "swefleet-dev"),
        database=os.getenv("NEO4J_DATABASE") or None,
    )
    store = Neo4jCommandStore(cfg)
    try:
        # Ensure unique id constraints for core labels we use
        store.init_constraints(["Case", "PlanVersion", "Decision", "Subtask", "Actor"])

        # Nodes
        store.upsert_entity("Case", case_id, {"title": "Demo Context Case"})
        store.upsert_entity(
            "PlanVersion",
            f"P-{case_id}",
            {
                "version": 1,
                "status": "DRAFT",
                "case_id": case_id,
            },
        )

        # Decisions
        store.upsert_entity("Decision", "D1", {"title": "Use Redis for planning state", "status": "PROPOSED"})
        store.upsert_entity("Decision", "D2", {"title": "Use Neo4j for decision graph", "status": "PROPOSED"})

        # Subtasks
        store.upsert_entity("Subtask", "S1", {"title": "Design Redis keys", "role": "architect"})
        store.upsert_entity("Subtask", "S2", {"title": "Model decisions in Neo4j", "role": "developer"})

        # Actor
        store.upsert_entity("Actor", "actor:planner", {"name": "Planner"})

        # Relationships
        store.relate(
            case_id,
            "HAS_PLAN",
            f"P-{case_id}",
            src_labels=["Case"],
            dst_labels=["PlanVersion"],
        )
        store.relate(
            f"P-{case_id}",
            "CONTAINS_DECISION",
            "D1",
            src_labels=["PlanVersion"],
            dst_labels=["Decision"],
        )
        store.relate(
            f"P-{case_id}",
            "CONTAINS_DECISION",
            "D2",
            src_labels=["PlanVersion"],
            dst_labels=["Decision"],
        )
        store.relate("D1", "INFLUENCES", "S1", src_labels=["Decision"], dst_labels=["Subtask"])
        store.relate("D2", "INFLUENCES", "S2", src_labels=["Decision"], dst_labels=["Subtask"])
        store.relate("D1", "AUTHORED_BY", "actor:planner", src_labels=["Decision"], dst_labels=["Actor"])
        store.relate("D2", "AUTHORED_BY", "actor:planner", src_labels=["Decision"], dst_labels=["Actor"])
        store.relate("D1", "DEPENDS_ON", "D2", src_labels=["Decision"], dst_labels=["Decision"])
    finally:
        store.close()


def main() -> None:
    case_id = os.getenv("DEMO_CASE_ID", "CTX-001")
    redis_url = os.getenv("REDIS_URL", "redis://:swefleet-dev@localhost:6379/0")

    print(f"Seeding Redis for case {case_id} -> {redis_url}")
    seed_redis_example(case_id, redis_url)

    print(f"Seeding Neo4j for case {case_id}")
    seed_neo4j_example(case_id)

    print("Done. You can now run the SessionRehydrationUseCase or reports.")


if __name__ == "__main__":
    main()


