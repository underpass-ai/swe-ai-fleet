"""Utility functions for context service."""


def detect_scopes(prompt_blocks) -> list[str]:
    """Detect which scopes are present in the prompt blocks based on content sections."""
    content = prompt_blocks.context
    if not content:
        return []

    scopes = []
    scopes.extend(detect_case_header_scope(content))
    scopes.extend(detect_plan_header_scope(content))
    scopes.extend(detect_subtasks_scope(content))
    scopes.extend(detect_decisions_scope(content))
    scopes.extend(detect_dependencies_scope(content))
    scopes.extend(detect_milestones_scope(content))

    return scopes


def detect_case_header_scope(content: str) -> list[str]:
    """Detect CASE_HEADER scope based on content."""
    if "Case:" in content or "Status:" in content:
        return ["CASE_HEADER"]
    return []


def detect_plan_header_scope(content: str) -> list[str]:
    """Detect PLAN_HEADER scope based on content."""
    if "Plan:" in content or "Total Subtasks:" in content:
        return ["PLAN_HEADER"]
    return []


def detect_subtasks_scope(content: str) -> list[str]:
    """Detect SUBTASKS_ROLE scope based on content."""
    has_subtasks = "Subtasks:" in content or "Your Subtasks:" in content
    has_no_subtasks = "No subtasks" in content
    if has_subtasks and not has_no_subtasks:
        return ["SUBTASKS_ROLE"]
    return []


def detect_decisions_scope(content: str) -> list[str]:
    """Detect DECISIONS_RELEVANT_ROLE scope based on content."""
    has_decisions = "Decisions:" in content or "Recent Decisions:" in content
    has_no_decisions = "No relevant decisions" in content
    if has_decisions and not has_no_decisions:
        return ["DECISIONS_RELEVANT_ROLE"]
    return []


def detect_dependencies_scope(content: str) -> list[str]:
    """Detect DEPS_RELEVANT scope based on content."""
    if "Dependencies:" in content or "Decision Dependencies:" in content:
        return ["DEPS_RELEVANT"]
    return []


def detect_milestones_scope(content: str) -> list[str]:
    """Detect MILESTONES scope based on content."""
    has_milestones = "Milestones:" in content or "Recent Milestones:" in content
    has_no_milestones = "No recent milestones" in content
    if has_milestones and not has_no_milestones:
        return ["MILESTONES"]
    return []

