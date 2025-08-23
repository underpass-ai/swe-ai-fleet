from __future__ import annotations

from importlib import import_module

import pytest

context_assembler = import_module("swe_ai_fleet.context.context_assembler")
RoleContextFields = import_module("swe_ai_fleet.context.domain.role_context_fields").RoleContextFields
PromptScopePolicy = import_module("swe_ai_fleet.context.domain.scopes.prompt_scope_policy").PromptScopePolicy


class _FakeBundle:
    def __init__(self, packs):
        self.packs = packs


class _FakeRehydrator:
    def __init__(self, bundle: _FakeBundle):
        self._bundle = bundle

    def build(self, _req):  # signature-compatible enough
        return self._bundle


def _make_pack_for(role: str = "dev") -> RoleContextFields:
    return RoleContextFields(
        role=role,
        case_header={"case_id": "C1", "title": "Build a thing"},
        plan_header={"plan_id": "P1", "rationale": "Do X then Y"},
        role_subtasks=[
            {
                "subtask_id": "S1",
                "title": "Implement A",
                "depends_on": ["S0"],
            },
            {"subtask_id": "S2", "title": "Implement B"},
        ],
        decisions_relevant=[
            {"id": "D1", "title": "Choose framework"},
            {"id": "D2", "title": "Pick database"},
        ],
        decision_dependencies=[{"src": "D1", "dst": "D2"}],
        impacted_subtasks=[{"subtask_id": "S1"}, {"subtask_id": "S2"}],
        recent_milestones=[{"id": f"M{i}", "ts_ms": i} for i in range(12)],
        last_summary=("Summary includes password: topsecret and Authorization: Bearer abc.def=="),
        token_budget_hint=4096,
    )


def test_narrow_pack_to_subtask_filters_fields():
    pack = _make_pack_for()
    narrowed = context_assembler._narrow_pack_to_subtask(pack, "S2")

    assert all(s["subtask_id"] == "S2" for s in narrowed.role_subtasks)
    assert all(i["subtask_id"] == "S2" for i in narrowed.impacted_subtasks)
    # trimmed to last 10
    assert len(narrowed.recent_milestones) == 10
    assert narrowed.recent_milestones[-1]["id"] == "M11"


def test_build_title_returns_case_title():
    pack = _make_pack_for()
    assert context_assembler._build_title(pack) == pack.case_header["title"]


def test_build_system_includes_role_and_title():
    system = context_assembler._build_system("dev", "Build a thing")
    assert "dev" in system and "Build a thing" in system


def test_build_context_composes_expected_lines():
    pack = _make_pack_for()
    ctx = context_assembler._build_context(pack, current_subtask_id="S1")
    assert "Case: C1 — Build a thing" in ctx
    assert "Plan rationale: Do X then Y" in ctx
    assert "Current subtask: S1" in ctx
    assert "Depends on:" in ctx
    assert "Relevant decisions: D1:Choose framework; D2:Pick database" in ctx
    assert "Last summary:" in ctx


def test_build_prompt_blocks_success_with_redaction():
    pack = _make_pack_for("dev")
    bundle = _FakeBundle(packs={"dev": pack})
    rehydrator = _FakeRehydrator(bundle)

    # Compute expected scopes and allow exactly those
    expected_scopes = pack.detect_scopes()
    policy = PromptScopePolicy({"exec": {"dev": sorted(expected_scopes)}})

    blocks = context_assembler.build_prompt_blocks(
        rehydrator=rehydrator,
        policy=policy,
        case_id="C1",
        role="dev",
        phase="exec",
        current_subtask_id="S1",
    )

    assert blocks.system.startswith("You are the dev agent")
    assert "Case: C1 — Build a thing" in blocks.context
    # redaction
    assert "password: [REDACTED]" in blocks.context
    assert "Bearer [REDACTED]" in blocks.context
    assert isinstance(blocks.tools, str) and len(blocks.tools) > 0


def test_build_prompt_blocks_raises_on_missing_scopes():
    pack = _make_pack_for("qa")
    bundle = _FakeBundle(packs={"qa": pack})
    rehydrator = _FakeRehydrator(bundle)

    # Require a scope that won't be present to trigger missing
    policy = PromptScopePolicy({"exec": {"qa": ["NON_EXISTENT_SCOPE"]}})

    with pytest.raises(ValueError):
        context_assembler.build_prompt_blocks(
            rehydrator=rehydrator,
            policy=policy,
            case_id="C1",
            role="qa",
            phase="exec",
        )
