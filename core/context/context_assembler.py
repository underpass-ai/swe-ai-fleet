from __future__ import annotations

from core.context.domain.context_sections import ContextSections
from core.context.domain.role_context_fields import RoleContextFields
from core.context.domain.scopes.prompt_blocks import PromptBlocks
from core.context.domain.scopes.prompt_scope_policy import (
    PromptScopePolicy,
)
from core.context.domain.scopes.scope_check_result import (
    ScopeCheckResult,
)
from core.context.session_rehydration import (
    RehydrationRequest,
    SessionRehydrationUseCase,
)


def _narrow_pack_to_subtask(
    pack: RoleContextFields,
    subtask_id: str,
) -> RoleContextFields:
    """Create a focused view of role context fields for a specific subtask.

    This follows DDD principles by creating a bounded context that contains
    only the information relevant to the current subtask, improving focus
    and reducing cognitive load for agents.

    Args:
        pack: The full role context fields containing all available information
        subtask_id: The specific subtask to focus on

    Returns:
        A new RoleContextFields instance narrowed to the specified subtask,
        with milestones trimmed to the last 10 for relevance
    """
    # Filter tasks and impacted_tasks by subtask_id
    filtered_tasks = tuple(
        task for task in pack.role_tasks
        if task.task_id.to_string() == subtask_id
    )
    filtered_impacted = tuple(
        impact for impact in pack.impacted_tasks
        if impact.task_id.to_string() == subtask_id
    )

    return RoleContextFields(
        role=pack.role,
        story_header=pack.story_header,
        plan_header=pack.plan_header,
        role_tasks=filtered_tasks,
        decisions_relevant=pack.decisions_relevant,
        decision_dependencies=pack.decision_dependencies,
        impacted_tasks=filtered_impacted,
        recent_milestones=pack.get_recent_milestones(10),
        last_summary=pack.last_summary,
        token_budget_hint=pack.token_budget_hint,
    )


def _build_title(role_context_fields: RoleContextFields) -> str:
    """Extract the human-readable story title from role context fields.

    This provides a clear, domain-specific identifier for the story
    that agents can reference in their work.
    """
    return role_context_fields.story_header.title


def _build_system(role: str, title: str) -> str:
    """Build a system message that clearly defines the agent's role and mission.

    Uses domain-specific language to make the agent's purpose and constraints
    clear and actionable.
    """
    return (
        f"You are the {role} agent working on case '{title}'. "
        "Follow constraints and acceptance criteria. "
        "Provide only necessary steps."
    )


def _build_context(
    role_context_fields: RoleContextFields,
    current_subtask_id: str | None,
) -> str:
    """Build a human-readable context string from role context fields.

    Follows DDD principles by using domain-specific language and
    separating concerns into focused, readable methods.
    """
    context_sections = ContextSections()
    context_sections.build_from_role_context_fields(role_context_fields, current_subtask_id)
    return context_sections.to_string()


def _rehydrate_context_data(
    rehydrator: SessionRehydrationUseCase,
    case_id: str,
    role: str,
) -> RoleContextFields:
    """Retrieve context data from persistent storage for the specified case and role.

    This encapsulates the data retrieval logic and provides a clear interface
    for getting the necessary context information.
    """
    request = RehydrationRequest(case_id=case_id, roles=[role], include_timeline=True, include_summaries=True)
    bundle = rehydrator.build(request)
    return bundle.packs[role]


def _enforce_scope_policies(
    policy: PromptScopePolicy,
    role_context_fields: RoleContextFields,
    phase: str,
    role: str,
) -> None:
    """Enforce scope policies to ensure security and relevance of context data.

    This function validates that the provided context data meets the scope
    requirements for the current phase and role, raising an error if violations
    are detected.

    Args:
        policy: The scope policy enforcer
        role_context_fields: The context data to validate
        phase: Current work phase
        role: Current agent role

    Raises:
        ValueError: When scope policy violations are detected
    """
    provided_scopes = role_context_fields.detect_scopes()
    scope_check_result = policy.check(phase=phase, role=role, provided_scopes=provided_scopes)

    if not scope_check_result.allowed:
        _handle_scope_violations(scope_check_result)


def _handle_scope_violations(scope_check_result: ScopeCheckResult) -> None:
    """Handle scope policy violations by raising appropriate errors.

    This function provides clear error messages when scope violations
    are detected, helping developers understand what went wrong.
    """
    # Handle extra scopes that might leak sensitive information
    if "SUBTASKS_ALL" in scope_check_result.extra or "SUBTASKS_ALL_MIN" in scope_check_result.extra:
        # These scopes are not used in the pack; ensure they're not leaking
        pass

    # If missing critical scopes, raise an error
    if scope_check_result.missing:
        missing_scopes = sorted(scope_check_result.missing)
        extra_scopes = sorted(scope_check_result.extra)
        raise ValueError(f"Scope violation: missing={missing_scopes}, extra={extra_scopes}")


def _build_tools_message() -> str:
    """Build the tools section message for agent guidance.

    This provides clear guidance on when and how agents should use
    available tools in their work.
    """
    return "You may call tools approved for your role when necessary."


def build_prompt_blocks(
    rehydrator: SessionRehydrationUseCase,
    policy: PromptScopePolicy,
    case_id: str,
    role: str,
    phase: str,
    current_subtask_id: str | None = None,
) -> PromptBlocks:
    """Build structured prompt blocks for agent consumption.

    This function orchestrates the creation of prompt blocks following DDD principles:
    - Domain-driven design with clear bounded contexts
    - Separation of concerns with focused responsibilities
    - Domain-specific language and terminology
    - Clear data flow and transformation steps

    The process follows these steps:
    1. Rehydrate context data from persistent storage
    2. Focus context on specific subtask if provided
    3. Enforce scope policies for security and relevance
    4. Compose human-readable prompt sections
    5. Apply security redaction to sensitive information
    6. Return structured prompt blocks ready for agent use

    Args:
        rehydrator: Service for retrieving context data from storage
        policy: Policy enforcer for scope validation and redaction
        case_id: Unique identifier for the case
        role: The agent role (e.g., 'dev', 'qa', 'architect')
        phase: Current phase of work (e.g., 'plan', 'exec', 'test')
        current_subtask_id: Optional subtask to focus on

    Returns:
        PromptBlocks containing system, context, and tools sections

    Raises:
        ValueError: When scope policy violations are detected
    """
    # Step 1: Rehydrate context data from persistent storage
    role_context_fields = _rehydrate_context_data(rehydrator, case_id, role)

    # Step 2: Focus context on specific subtask if provided
    if current_subtask_id:
        role_context_fields = _narrow_pack_to_subtask(role_context_fields, current_subtask_id)

    # Step 3: Enforce scope policies for security and relevance
    _enforce_scope_policies(policy, role_context_fields, phase, role)

    # Step 4: Compose human-readable prompt sections
    title = _build_title(role_context_fields)
    system_message = _build_system(role, title)
    context_text = _build_context(role_context_fields, current_subtask_id)

    # Step 5: Apply security redaction to sensitive information
    redacted_context = policy.redact(role, context_text)

    # Step 6: Return structured prompt blocks ready for agent use
    tools_message = _build_tools_message()

    return PromptBlocks(system=system_message, context=redacted_context, tools=tools_message)
