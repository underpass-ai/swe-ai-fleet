import json
from unittest.mock import MagicMock

import pytest

from core.reports.adapters.redis_planning_read_adapter import (
    RedisPlanningReadAdapter,
)
from core.reports.domain.report import Report


@pytest.fixture()
def fake_redis() -> MagicMock:
    return MagicMock()


def make_adapter_with(fake_r: MagicMock) -> RedisPlanningReadAdapter:
    return RedisPlanningReadAdapter(fake_r)


def test_get_case_spec_found(fake_redis: MagicMock):
    payload = {
        "case_id": "C1",
        "title": "Title",
        "description": "Desc",
        "acceptance_criteria": ["a"],
        "constraints": {"k": "v"},
        "requester_id": "U1",
        "tags": ["t1"],
        "created_at_ms": 42,
    }
    fake_redis.get.return_value = json.dumps(payload)

    adapter = make_adapter_with(fake_redis)
    dto = adapter.get_case_spec("C1")

    assert dto is not None
    assert dto.case_id == "C1"
    assert dto.acceptance_criteria == ["a"]
    assert dto.constraints == {"k": "v"}
    fake_redis.get.assert_called_once_with(adapter._k_spec("C1"))


def test_get_case_spec_missing(fake_redis: MagicMock):
    fake_redis.get.return_value = None
    adapter = make_adapter_with(fake_redis)
    assert adapter.get_case_spec("C1") is None


def test_get_plan_draft_parses_subtasks(fake_redis: MagicMock):
    payload = {
        "plan_id": "P1",
        "case_id": "C1",
        "version": 2,
        "status": "draft",
        "author_id": "U1",
        "rationale": "because",
        "created_at_ms": 99,
        "subtasks": [
            {
                "subtask_id": "S1",
                "title": "T1",
                "description": "D1",
                "role": "dev",
                "suggested_tech": ["python"],
                "depends_on": ["S0"],
                "estimate_points": 3.5,
                "priority": 1,
                "risk_score": 0.2,
                "notes": "note",
            }
        ],
    }
    fake_redis.get.return_value = json.dumps(payload)

    adapter = make_adapter_with(fake_redis)
    pv = adapter.get_plan_draft("C1")

    assert pv is not None
    assert pv.plan_id == "P1"
    assert len(pv.subtasks) == 1
    st = pv.subtasks[0]
    assert st.subtask_id == "S1"
    assert st.suggested_tech == ["python"]
    fake_redis.get.assert_called_once_with(adapter._k_draft("C1"))


def test_get_plan_draft_missing(fake_redis: MagicMock):
    fake_redis.get.return_value = None
    adapter = make_adapter_with(fake_redis)
    assert adapter.get_plan_draft("C1") is None


def test_get_planning_events_parses_and_orders(fake_redis: MagicMock):
    # Redis xrevrange returns newest-first; adapter reverses to oldest-first
    fake_redis.xrevrange.return_value = [
        ("2-0", {"event": "B", "actor": "u", "payload": "{\"b\":1}", "ts": "2"}),
        ("1-0", {"event": "A", "actor": "u", "payload": "{\"a\":1}", "ts": "1"}),
    ]

    adapter = make_adapter_with(fake_redis)
    events = adapter.get_planning_events("C1", count=2)

    assert [e.id for e in events] == ["1-0", "2-0"]
    assert events[0].payload == {"a": 1}
    assert events[1].payload == {"b": 1}
    fake_redis.xrevrange.assert_called_once_with(adapter._k_stream("C1"), count=2)


def test_get_planning_events_handles_bad_payload(fake_redis: MagicMock):
    fake_redis.xrevrange.return_value = [
        ("1-0", {"event": "A", "actor": "u", "payload": "not-json", "ts": "1"}),
    ]

    adapter = make_adapter_with(fake_redis)
    events = adapter.get_planning_events("C1", count=1)

    assert events[0].payload == {"raw": "not-json"}


def test_save_report_writes_all_keys_with_ttl(fake_redis: MagicMock):
    adapter = make_adapter_with(fake_redis)
    fake_pipe = MagicMock()
    fake_redis.pipeline.return_value = fake_pipe

    report = Report(
        case_id="C1",
        plan_id="P1",
        generated_at_ms=123,
        markdown="# rpt",
    )

    adapter.save_report(case_id="C1", report=report, ttl_seconds=60)

    report_id = "123"
    key_doc = adapter._k_report_doc("C1", report_id)
    key_list = adapter._k_report_list("C1")
    key_last = adapter._k_report_last("C1")

    fake_redis.pipeline.assert_called_once()
    # Validate doc content was json-dumped (inspect the specific set call)
    set_calls = fake_pipe.set.call_args_list
    doc_set_call = next(call for call in set_calls if call.args[0] == key_doc)
    doc = json.loads(doc_set_call.args[1])
    assert doc["case_id"] == "C1"
    assert doc["plan_id"] == "P1"
    assert doc["generated_at_ms"] == 123

    fake_pipe.lpush.assert_called_once_with(key_list, report_id)
    fake_pipe.set.assert_any_call(key_last, report_id, ex=60)
    fake_pipe.expire.assert_called_once_with(key_list, 60)
    fake_pipe.execute.assert_called_once()
