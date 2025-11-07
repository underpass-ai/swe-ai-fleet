"""ScopeEnum: Enumeration of action scopes in the RBAC system."""

from enum import Enum


class ScopeEnum(str, Enum):
    """
    Enumeration of action scopes.

    Scopes enforce role boundaries:
    - Architect operates in TECHNICAL scope
    - PO operates in BUSINESS scope
    - QA operates in QUALITY scope
    - DevOps operates in OPERATIONS scope
    - Data operates in DATA scope
    - WORKFLOW is cross-cutting (system operations)
    """

    TECHNICAL = "technical"
    BUSINESS = "business"
    QUALITY = "quality"
    OPERATIONS = "operations"
    DATA = "data"
    WORKFLOW = "workflow"

