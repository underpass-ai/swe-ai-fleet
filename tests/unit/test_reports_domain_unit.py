from dataclasses import FrozenInstanceError

import pytest

from swe_ai_fleet.reports.domain.report import Report
from swe_ai_fleet.reports.domain.report_request import ReportRequest


def test_reportrequest_defaults_and_frozen():
    rr = ReportRequest(case_id="CASE-1")

    assert rr.max_events == 200
    assert rr.include_constraints is True
    assert rr.include_acceptance is True
    assert rr.include_timeline is True
    assert rr.include_dependencies is True
    assert rr.persist_to_redis is True
    assert rr.ttl_seconds == 14 * 24 * 3600

    with pytest.raises(FrozenInstanceError):
        rr.include_timeline = False


def test_reportrequest_equality():
    a = ReportRequest(case_id="C1")
    b = ReportRequest(case_id="C1")
    assert a == b


def test_report_defaults_and_frozen():
    rpt = Report(
        case_id="C1",
        plan_id=None,
        generated_at_ms=123456,
        markdown="# Report\n",
    )

    assert rpt.stats == {}

    with pytest.raises(FrozenInstanceError):
        rpt.markdown = "updated"


def test_report_stats_default_factory_independence():
    a = Report(case_id="C1", plan_id=None, generated_at_ms=1, markdown="m")
    b = Report(case_id="C2", plan_id=None, generated_at_ms=2, markdown="m")

    assert a.stats is not b.stats

    a.stats["k"] = "v"
    assert b.stats == {}


def test_report_hashing_raises_due_to_mutable_field():
    rpt = Report(case_id="C1", plan_id=None, generated_at_ms=1, markdown="m")
    with pytest.raises(TypeError):
        hash(rpt)
