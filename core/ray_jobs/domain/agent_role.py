"""Agent role enum and role contexts."""

from enum import Enum


class AgentRole(str, Enum):
    """Roles de agentes en el sistema."""
    DEV = "DEV"
    QA = "QA"
    ARCHITECT = "ARCHITECT"
    DEVOPS = "DEVOPS"
    DATA = "DATA"
    TASK_EXTRACTOR = "TASK_EXTRACTOR"  # Special role for extracting tasks from deliberations


# Domain knowledge: Role contexts (constantes de dominio)
ROLE_CONTEXTS = {
    AgentRole.DEV: (
        "You are an expert software developer. Focus on writing clean, "
        "maintainable, well-tested code following best practices."
    ),
    AgentRole.QA: (
        "You are an expert quality assurance engineer. Focus on testing "
        "strategies, edge cases, and potential bugs."
    ),
    AgentRole.ARCHITECT: (
        "You are a senior software architect. Focus on system design, "
        "scalability, and architectural patterns."
    ),
    AgentRole.DEVOPS: (
        "You are a DevOps engineer. Focus on deployment, CI/CD, "
        "infrastructure, and reliability."
    ),
    AgentRole.DATA: (
        "You are a data engineer. Focus on data pipelines, ETL, "
        "databases, and data quality."
    ),
    AgentRole.TASK_EXTRACTOR: (
        "You are a task extraction specialist. Analyze agent deliberations "
        "and extract concrete, actionable tasks for implementation."
    ),
}


def get_role_context(role: str | AgentRole) -> str:
    """
    Obtener contexto base para un rol.

    Args:
        role: Role del agente

    Returns:
        Contexto base como string
    """
    try:
        role_enum = AgentRole(role) if isinstance(role, str) else role
        return ROLE_CONTEXTS[role_enum]
    except (ValueError, KeyError):
        return f"You are an expert {role} engineer."

