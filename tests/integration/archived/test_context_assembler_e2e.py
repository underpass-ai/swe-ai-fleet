from __future__ import annotations

import json
import time
from typing import Any, cast

import pytest
import redis
from core.context.adapters.redis_planning_read_adapter import (
    RedisPlanningReadAdapter,
)
from core.context.context_assembler import build_prompt_blocks
from core.context.domain.rehydration_request import RehydrationRequest
from core.context.domain.scopes.prompt_scope_policy import (
    PromptScopePolicy,
)
from core.context.session_rehydration import SessionRehydrationUseCase
from core.memory.adapters.redis_store import RedisKvPort
from core.reports.domain.decision_edges import DecisionEdges
from core.reports.domain.decision_node import DecisionNode
from core.reports.domain.subtask_node import SubtaskNode
from core.reports.dtos.dtos import PlanVersionDTO


def _k_spec(case_id: str) -> str:
    return f"swe:case:{case_id}:spec"


def _k_draft(case_id: str) -> str:
    return f"swe:case:{case_id}:planning:draft"


def _k_stream(case_id: str) -> str:
    return f"swe:case:{case_id}:planning:stream"


def _k_summary_last(case_id: str) -> str:
    return f"swe:case:{case_id}:summaries:last"


def _cleanup_case(r: redis.Redis, case_id: str) -> None:
    keys = [
        _k_spec(case_id),
        _k_draft(case_id),
        _k_stream(case_id),
        _k_summary_last(case_id),
    ]
    handoff_prefix = f"swe:case:{case_id}:handoff:"
    handoff_keys = list(cast(list[str], r.keys(f"{handoff_prefix}*")))
    if handoff_keys:
        keys.extend(handoff_keys)
    if keys:
        r.delete(*keys)


class _FakeGraphAdapter:
    def __init__(
        self,
        plan: PlanVersionDTO | None,
        decisions: list[DecisionNode],
        deps: list[DecisionEdges],
        impacts: list[tuple[str, SubtaskNode]],
    ) -> None:
        self._plan = plan
        self._decisions = decisions
        self._deps = deps
        self._impacts = impacts

    def get_plan_by_case(self, case_id: str) -> PlanVersionDTO | None:
        return self._plan

    def list_decisions(self, case_id: str) -> list[DecisionNode]:
        return self._decisions

    def list_decision_dependencies(self, case_id: str) -> list[DecisionEdges]:
        return self._deps

    def list_decision_impacts(self, case_id: str) -> list[tuple[str, SubtaskNode]]:
        return self._impacts


class _KvShim(RedisKvPort):  # type: ignore[misc]
    def __init__(self, client: redis.Redis) -> None:
        self._c = client

    def get(self, key: str):  # type: ignore[override]
        return self._c.get(key)

    def xrevrange(self, key: str, count: int | None = None):  # type: ignore[override]
        return self._c.xrevrange(key, count=count)

    def pipeline(self):  # type: ignore[override]
        return self._c.pipeline()


def test_context_assembler_e2e_build_prompt_blocks_for_developer() -> None:
    url = "redis://:swefleet-dev@localhost:6379/0"
    try:
        r: redis.Redis = redis.Redis.from_url(url, decode_responses=True)
        # quick connectivity check; skip if redis is not available
        r.ping()
    except Exception:  # pragma: no cover - environment dependent
        pytest.skip("Redis is not available on localhost:6379")

    case_id = f"e2e-ctx-asm-{int(time.time())}"
    _cleanup_case(r, case_id)

    # Seed case spec
    spec_doc: dict[str, Any] = {
        "case_id": case_id,
        "title": "Context Assembler E2E",
        "description": "Build prompt blocks end-to-end",
        "acceptance_criteria": ["blocks"],
        "constraints": {"env": "dev"},
        "requester_id": "user-1",
        "tags": ["e2e"],
        "created_at_ms": int(time.time() * 1000),
    }
    r.set(_k_spec(case_id), json.dumps(spec_doc))

    # Seed plan draft with one developer subtask
    draft_doc: dict[str, Any] = {
        "plan_id": "P1",
        "case_id": case_id,
        "version": 1,
        "status": "draft",
        "author_id": "bot",
        "rationale": "because",
        "created_at_ms": int(time.time() * 1000),
        "subtasks": [
            {
                "subtask_id": "S1",
                "title": "Implement",
                "description": "Do it",
                "role": "developer",
                "depends_on": [],
            }
        ],
    }
    r.set(_k_draft(case_id), json.dumps(draft_doc))

    # Seed timeline events
    r.xadd(
        _k_stream(case_id),
        {"event": "create_case_spec", "actor": "user", "payload": json.dumps({}), "ts": "1"},
    )
    r.xadd(
        _k_stream(case_id),
        {"event": "approve_plan", "actor": "po", "payload": json.dumps({}), "ts": "2"},
    )

    # Last summary includes secrets to test redaction
    r.set(_k_summary_last(case_id), "password = hunter2; Authorization: Bearer abc.def==")

    # Build fake graph adapter data
    plan = PlanVersionDTO(
        plan_id="P1",
        case_id=case_id,
        version=1,
        status="approved",
        author_id="bot",
    )
    decisions = [
        DecisionNode(
            id="D1",
            title="Choose DB",
            rationale="Postgres",
            status="accepted",
            created_at_ms=int(time.time() * 1000),
            author_id="arch",
        )
    ]
    deps = []
    impacts = [("D1", SubtaskNode(id="S1", title="Implement", role="developer"))]

    planning_adapter = RedisPlanningReadAdapter(_KvShim(r))
    graph_adapter = _FakeGraphAdapter(plan, decisions, deps, impacts)
    usecase = SessionRehydrationUseCase(planning_adapter, graph_adapter)

    # Compute expected scopes for policy from the real bundle
    req = RehydrationRequest(
        case_id=case_id,
        roles=["developer"],
        include_timeline=True,
        include_summaries=True,
    )
    bundle = usecase.build(req)
    dev_pack = bundle.packs["developer"]
    expected_scopes = sorted(dev_pack.detect_scopes())

    policy = PromptScopePolicy({"exec": {"developer": expected_scopes}})

    # Build prompt blocks end-to-end
    blocks = build_prompt_blocks(
        rehydrator=usecase,
        policy=policy,
        case_id=case_id,
        role="developer",
        phase="exec",
        current_subtask_id="S1",
    )

    assert blocks.system.startswith("You are the developer agent")
    assert "Case: " in blocks.context and "Context Assembler E2E" in blocks.context
    # Redaction asserted
    assert "password: [REDACTED]" in blocks.context
    assert "Bearer [REDACTED]" in blocks.context
