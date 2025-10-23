from importlib import import_module

RoleContextFields = import_module("core.context.domain.role_context_fields").RoleContextFields


def test_filter_role_subtasks_by_id_returns_only_matches():
    pack = RoleContextFields(
        role="developer",
        case_header={},
        plan_header={},
        role_subtasks=[
            {"subtask_id": "S1", "title": "Do A"},
            {"subtask_id": "S2", "title": "Do B"},
        ],
    )
    result = pack.filter_role_subtasks_by_id("S2")
    assert len(result) == 1
    assert result[0]["subtask_id"] == "S2"


def test_detect_scopes_for_developer_role_with_many_items():
    role_subtasks = [{"subtask_id": f"S{i}", "title": f"T{i}"} for i in range(7)]
    pack = RoleContextFields(
        role="developer",
        case_header={"case_id": "C1"},
        plan_header={"plan_id": "P1"},
        role_subtasks=role_subtasks,
        decisions_relevant=[{"id": "D1"}],
        decision_dependencies=[{"from": "D1", "to": "D2"}],
        impacted_subtasks=[{"subtask_id": "S1"}],
        recent_milestones=[{"id": "M1"}],
        last_summary="Summary text",
    )
    scopes = pack.detect_scopes()
    # Base scopes
    assert "CASE_HEADER" in scopes
    assert "PLAN_HEADER" in scopes
    assert "DECISIONS_RELEVANT_ROLE" in scopes
    assert "DEPS_RELEVANT" in scopes
    assert "SUBTASKS_ROLE" in scopes
    assert "SUBTASKS_ROLE_MIN" in scopes  # > 5 role_subtasks
    assert "MILESTONES" in scopes
    assert "SUMMARY_LAST" in scopes
    # No QA/architect heuristics for developer
    assert "DECISIONS_GLOBAL" not in scopes
    assert "SUBTASKS_ALL_MIN" not in scopes


def test_detect_scopes_for_qa_role_applies_heuristics():
    role_subtasks = [{"subtask_id": f"S{i}", "title": f"T{i}"} for i in range(6)]
    pack = RoleContextFields(
        role="qa",
        case_header={"case_id": "C1"},
        plan_header={"plan_id": "P1"},
        role_subtasks=role_subtasks,
        decisions_relevant=[{"id": "D1"}],
        impacted_subtasks=[{"subtask_id": "S1"}],
    )
    scopes = pack.detect_scopes()
    # Heuristic changes: replace role decisions with global and add SUBTASKS_ALL_MIN
    assert "DECISIONS_RELEVANT_ROLE" not in scopes
    assert "DECISIONS_GLOBAL" in scopes
    assert "SUBTASKS_ROLE" in scopes
    assert "SUBTASKS_ALL_MIN" in scopes
    # SUBTASKS_ROLE_MIN also applies since len(role_subtasks) > 5
    assert "SUBTASKS_ROLE_MIN" in scopes


def test_get_recent_milestones_handles_limits():
    milestones = [{"id": f"M{i}"} for i in range(1, 8)]  # M1..M7
    pack = RoleContextFields(
        role="dev",
        case_header={},
        plan_header={},
        recent_milestones=milestones,
    )
    # default limit 10 returns all available (last up to 10)
    assert pack.get_recent_milestones() == milestones[-10:]
    # explicit positive limit returns last N
    assert pack.get_recent_milestones(3) == milestones[-3:]
    # non-positive returns empty
    assert pack.get_recent_milestones(0) == []
    assert pack.get_recent_milestones(-5) == []


def test_filter_impacted_subtasks_by_id_filters_correctly():
    impacted = [
        {"subtask_id": "S1", "impact": "high"},
        {"subtask_id": "S2", "impact": "low"},
        {"subtask_id": "S1", "impact": "medium"},
    ]
    pack = RoleContextFields(
        role="dev",
        case_header={},
        plan_header={},
        impacted_subtasks=impacted,
    )
    result = pack.filter_impacted_subtasks_by_id("S1")
    assert len(result) == 2
    assert all(item["subtask_id"] == "S1" for item in result)


def test_build_current_subtask_context_lines_composes_lines():
    pack = RoleContextFields(
        role="dev",
        case_header={},
        plan_header={},
        role_subtasks=[
            {
                "subtask_id": "S100",
                "title": "Implement feature",
                "depends_on": ["S50", "S60"],
            }
        ],
    )
    lines = pack.build_current_subtask_context_lines()
    assert any(line.startswith("Current subtask: S100 — Implement feature") for line in lines)
    assert any(line.startswith("Depends on: S50, S60") for line in lines)

    # When no role_subtasks present, returns empty list
    empty_pack = RoleContextFields(role="dev", case_header={}, plan_header={})
    assert empty_pack.build_current_subtask_context_lines() == []
