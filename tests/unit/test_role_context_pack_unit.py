from __future__ import annotations

from dataclasses import FrozenInstanceError
from importlib import import_module

import pytest

RoleContextFields = import_module("swe_ai_fleet.context.domain.role_context_fields").RoleContextFields


def test_defaults_and_getitem():
    pack = RoleContextFields(
        role="dev",
        case_header={"case_id": "C1"},
        plan_header={"plan_id": "P1"},
    )

    assert pack.role == "dev"
    assert pack.case_header["case_id"] == "C1"
    assert pack.plan_header["plan_id"] == "P1"

    # Defaults
    assert pack.role_subtasks == []
    assert pack.decisions_relevant == []
    assert pack.decision_dependencies == []
    assert pack.impacted_subtasks == []
    assert pack.recent_milestones == []
    assert pack.last_summary is None
    assert pack.token_budget_hint == 8192

    # Dict-style access via __getitem__
    assert pack["role"] == "dev"
    assert isinstance(pack["case_header"], dict)


def test_frozen_role_context_fields():
    pack = RoleContextFields(role="qa", case_header={}, plan_header={})
    with pytest.raises(FrozenInstanceError):
        pack.role = "changed"  # type: ignore[attr-defined]
