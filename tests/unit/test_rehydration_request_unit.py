from __future__ import annotations

from dataclasses import FrozenInstanceError
from importlib import import_module

import pytest

RehydrationRequest = import_module("swe_ai_fleet.context.domain.rehydration_request").RehydrationRequest


def test_defaults_and_fields():
    req = RehydrationRequest(case_id="C1", roles=["architect", "devops"])

    assert req.case_id == "C1"
    assert req.roles == ["architect", "devops"]
    assert req.include_timeline is True
    assert req.timeline_events == 100
    assert req.include_summaries is True
    assert req.persist_handoff_bundle is True
    assert req.ttl_seconds == 7 * 24 * 3600


def test_frozen_rehydration_request():
    req = RehydrationRequest(case_id="C2", roles=["qa"])
    with pytest.raises(FrozenInstanceError):
        req.case_id = "changed"  # type: ignore[attr-defined]
