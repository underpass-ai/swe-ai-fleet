from __future__ import annotations

import json
from importlib import import_module
from typing import Any

import pytest

RedisPlanningReadAdapter = import_module(
    "swe_ai_fleet.context.adapters.redis_planning_read_adapter"
).RedisPlanningReadAdapter
_dtos_mod = import_module("swe_ai_fleet.reports.dtos.dtos")
CaseSpecDTO = _dtos_mod.CaseSpecDTO
PlanVersionDTO = _dtos_mod.PlanVersionDTO
SubtaskPlanDTO = _dtos_mod.SubtaskPlanDTO


class _RedisFake:
    def __init__(self) -> None:
        self.store: dict[str, Any] = {}
        self.streams: dict[str, list[tuple[str, dict[str, Any]]]] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def set(
        self,
        key: str,
        val: str,
        _ex: int | None = None,
    ) -> None:
        self.store[key] = val

    def xrevrange(
        self,
        key: str,
        count: int = 200,
    ):  # noqa: ANN001 - mimic redis
        return list(reversed(self.streams.get(key, [])[:count]))

    class _Pipe:
        def __init__(self, parent: _RedisFake) -> None:
            self._p = parent

        def set(self, key: str, val: str, ex: int | None = None):  # noqa: ANN001
            self._p.set(key, val, _ex=ex)
            return self

        def execute(self) -> list[Any]:  # noqa: ANN401
            return []

    def pipeline(self) -> _RedisFake._Pipe:
        return _RedisFake._Pipe(self)


def _mk_adapter(monkeypatch: pytest.MonkeyPatch):
    fake = _RedisFake()
    del monkeypatch  # silence unused param

    return RedisPlanningReadAdapter(fake), fake


def test_get_case_spec_and_draft(monkeypatch: pytest.MonkeyPatch):
    adapter, fake = _mk_adapter(monkeypatch)
    key_spec = adapter._k_spec("C1")
    key_draft = adapter._k_draft("C1")

    fake.set(
        key_spec,
        json.dumps(
            {
                "case_id": "C1",
                "title": "Title",
                "description": "d",
                "acceptance_criteria": ["a"],
                "constraints": {"c": 1},
                "requester_id": "u",
                "tags": ["t"],
                "created_at_ms": 1,
            }
        ),
    )

    fake.set(
        key_draft,
        json.dumps(
            {
                "plan_id": "P1",
                "case_id": "C1",
                "version": 2,
                "status": "DRAFT",
                "author_id": "u2",
                "rationale": "r",
                "subtasks": [
                    {
                        "subtask_id": "S1",
                        "title": "T",
                        "role": "dev",
                    }
                ],
                "created_at_ms": 3,
            }
        ),
    )

    spec = adapter.get_case_spec("C1")
    assert isinstance(spec, CaseSpecDTO)
    draft = adapter.get_plan_draft("C1")
    assert isinstance(draft, PlanVersionDTO)
    assert isinstance(draft.subtasks[0], SubtaskPlanDTO)


def test_get_planning_events_and_summary_and_handoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter, fake = _mk_adapter(monkeypatch)
    key_stream = adapter._k_stream("C1")
    fake.streams[key_stream] = [
        (
            "1-1",
            {
                "event": "approve_plan",
                "actor": "po",
                "payload": json.dumps({}),
                "ts": "3",
            },
        ),
        (
            "1-0",
            {
                "event": "create_case_spec",
                "actor": "sys",
                "payload": json.dumps({}),
                "ts": "1",
            },
        ),
    ]

    events = adapter.get_planning_events("C1", count=5)
    events_list = [e.event for e in events]
    assert events_list == ["create_case_spec", "approve_plan"]

    fake.set(adapter._k_summary_last("C1"), "SUM")
    assert adapter.read_last_summary("C1") == "SUM"

    adapter.save_handoff_bundle("C1", {"hello": "world"}, ttl_seconds=5)
    # Ensure a handoff key was written
    assert any(k.startswith("swe:case:C1:handoff:") for k in fake.store)
