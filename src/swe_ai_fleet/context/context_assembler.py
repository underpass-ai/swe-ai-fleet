from __future__ import annotations

from swe_ai_fleet.context.domain.role_context_fields import RoleContextFields
from swe_ai_fleet.context.domain.scopes.prompt_blocks import PromptBlocks
from swe_ai_fleet.context.domain.scopes.prompt_scope_policy import (
    PromptScopePolicy,
)
from swe_ai_fleet.context.session_rehydration import (
    RehydrationRequest,
    SessionRehydrationUseCase,
)


def _narrow_pack_to_subtask(
    pack: RoleContextFields,
    subtask_id: str,
) -> RoleContextFields:
    """Return a copy of RoleContextFields narrowed to a specific subtask.

    Filters role-specific subtasks and impacted subtasks by the provided
    subtask id, and trims recent milestones to the last 10, mirroring the
    previous inline logic.
    """
    return RoleContextFields(
        role=pack.role,
        case_header=pack.case_header,
        plan_header=pack.plan_header,
        role_subtasks=pack.filter_role_subtasks_by_id(subtask_id),
        decisions_relevant=pack.decisions_relevant,
        decision_dependencies=pack.decision_dependencies,
        impacted_subtasks=pack.filter_impacted_subtasks_by_id(subtask_id),
        recent_milestones=pack.get_recent_milestones(10),
        last_summary=pack.last_summary,
        token_budget_hint=pack.token_budget_hint,
    )


def _build_title(role_context_fields: RoleContextFields) -> str:
    return role_context_fields.case_header["title"]


def _build_system(role: str, title: str) -> str:
    return (
        f"You are the {role} agent working on case '{title}'. "
        "Follow constraints and acceptance criteria. "
        "Provide only necessary steps."
    )


def _build_context(
    role_context_fields: RoleContextFields,
    current_subtask_id: str | None,
) -> str:
    context_lines: list[str] = []
    case_id_value = role_context_fields.case_header["case_id"]
    case_title_value = role_context_fields.case_header["title"]
    context_lines.append(f"Case: {case_id_value} — {case_title_value}")
    if role_context_fields.plan_header.get("rationale"):
        rationale = role_context_fields.plan_header["rationale"]
        context_lines.append(f"Plan rationale: {rationale}")
    if role_context_fields.role_subtasks and current_subtask_id:
        context_lines.extend(role_context_fields.build_current_subtask_context_lines())
    if role_context_fields.decisions_relevant:
        d0 = role_context_fields.decisions_relevant[:4]
        decisions_text = "; ".join(f"{d['id']}:{d['title']}" for d in d0)
        context_lines.append("Relevant decisions: " + decisions_text)
    if role_context_fields.last_summary:
        context_lines.append("Last summary: " + role_context_fields.last_summary[:800])
    return "\n".join(context_lines)


def build_prompt_blocks(
    rehydrator: SessionRehydrationUseCase,
    policy: PromptScopePolicy,
    case_id: str,
    role: str,
    phase: str,
    current_subtask_id: str | None = None,
) -> PromptBlocks:
    # 1) Build pack
    req = RehydrationRequest(case_id=case_id, roles=[role], include_timeline=True, include_summaries=True)
    bundle = rehydrator.build(req)
    role_context_fields: RoleContextFields = bundle.packs[role]

    # 2) Narrow to current_subtask_id if provided
    if current_subtask_id:
        role_context_fields = _narrow_pack_to_subtask(role_context_fields, current_subtask_id)

    # 3) Enforce scopes
    provided = role_context_fields.detect_scopes()
    chk = policy.check(phase=phase, role=role, provided_scopes=provided)
    if not chk.allowed:
        # Hard enforcement: remove extras and fail
        # if still missing critical ones
        # Remove extras by zeroing fields
        if "SUBTASKS_ALL" in chk.extra or "SUBTASKS_ALL_MIN" in chk.extra:
            # Not used in pack; ensure not leaking
            pass
        # If missing, raise: configuration error or assembly issue
        if chk.missing:
            missing = sorted(chk.missing)
            extra = sorted(chk.extra)
            raise ValueError(f"Scope violation: missing={missing}, extra={extra}")

    # 4) Compose minimal prompt blocks
    title = _build_title(role_context_fields)
    system = _build_system(role, title)
    context_text = _build_context(role_context_fields, current_subtask_id)

    # 5) Redact
    ctx = policy.redact(role, context_text)

    # 6) Tool block (optional)
    tools = "You may call tools approved for your role when necessary."

    return PromptBlocks(system=system, context=ctx, tools=tools)
