from __future__ import annotations

from typing import Any

from swe_ai_fleet.reports.adapters.redis_planning_read_adapter import (
    RedisPlanningReadAdapter,
)


class FakeClient:
    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.streams: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        self.lists: dict[str, list[str]] = {}

    # Minimal methods used by adapter
    def get(self, key: str) -> str | None:
        return self.kv.get(key)

    def xrevrange(self, key: str, count: int | None = None):
        items = list(self.streams.get(key, []))
        items.reverse()
        if count is not None:
            items = items[: int(count)]
        return items

    def pipeline(self):  # noqa: D401
        client = self

        class P:
            def __init__(self) -> None:
                self.ops: list[tuple[str, tuple[Any, ...]]] = []

            def set(self, key: str, val: str, ex: int | None = None):  # noqa: ANN001,B032
                self.ops.append(("set", (key, val, ex)))

            def lpush(self, key: str, val: str):  # noqa: ANN001
                self.ops.append(("lpush", (key, val)))

            def expire(self, key: str, seconds: int):  # noqa: ANN001
                self.ops.append(("expire", (key, seconds)))

            def execute(self):
                for op, args in self.ops:
                    if op == "set":
                        k, v, _ex = args
                        client.kv[k] = v
                    elif op == "lpush":
                        k, v = args
                        client.lists.setdefault(k, []).insert(0, v)
                    elif op == "expire":
                        pass
                return []

        return P()

    # Optional methods for helpers
    def scan(self, cursor: int = 0, match: str | None = None, count: int | None = None):  # noqa: ARG002
        import re

        all_keys = list(self.kv.keys())
        if not match:
            return (0, all_keys)
        # Very small glob matcher: translate * to .*
        pattern = "^" + re.escape(match).replace("\\*", ".*") + "$"
        rx = re.compile(pattern)
        keys = [k for k in all_keys if rx.match(k)]
        if count is not None:
            keys = keys[: int(count)]
        return (0, keys)

    def hgetall(self, key: str) -> dict[str, Any]:  # noqa: D401
        return self.kv.get(key, {})  # type: ignore[return-value]

    def hget(self, key: str, field: str) -> Any:  # noqa: ANN401
        return self.kv.get(key, {}).get(field)


def test_get_case_spec_and_save_report_roundtrip() -> None:
    import json

    fc = FakeClient()
    adapter = RedisPlanningReadAdapter(client=fc)  # type: ignore[arg-type]

    # prepare a spec
    spec_key = adapter._k_spec("C1")
    fc.kv[spec_key] = json.dumps(
        {
            "case_id": "C1",
            "title": "T",
            "description": "D",
            "acceptance_criteria": ["A"],
            "constraints": {"k": "v"},
        }
    )

    spec = adapter.get_case_spec("C1")
    assert spec and spec.case_id == "C1"

    # save a report
    from swe_ai_fleet.reports.domain.report import Report

    r = Report(case_id="C1", plan_id="P1", generated_at_ms=1, markdown="# md", stats={})
    adapter.save_report("C1", r, ttl_seconds=60)
    # check last key exists
    last_key = adapter._k_report_last("C1")
    assert fc.kv[last_key] == "1"


def test_list_llm_sessions_and_events() -> None:
    fc = FakeClient()
    adapter = RedisPlanningReadAdapter(client=fc)  # type: ignore[arg-type]

    # two sessions with meta
    fc.kv[adapter._k_session_meta("S1")] = {"case_id": "C1", "role": "dev"}
    fc.kv[adapter._k_session_meta("S2")] = {"case_id": "C2", "role": "qa"}

    # add stream entries for S1
    fc.streams[adapter._k_session_stream("S1")] = [
        ("1-0", {"type": "llm_call", "model": "m", "content": "hi"}),
        ("2-0", {"type": "llm_response", "model": "m", "content": "yo"}),
    ]

    sessions = adapter.list_llm_sessions_for_case("C1", max_sessions=5)
    assert sessions and sessions[0][0] == "S1"
    # fetch events
    events = adapter.get_llm_events_for_session("S1", count=10)
    assert len(events) == 2 and events[0]["id"] == "1-0"
