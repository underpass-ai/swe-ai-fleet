"""Core shared domain objects for the SWE AI Fleet system.

Shared Kernel (DDD):
- Action, ActionEnum, ScopeEnum (RBAC actions)
- These are shared between bounded contexts (agents_and_tools, workflow)
- Changes here affect multiple services
"""

from core.shared.domain.action import Action
from core.shared.domain.action_enum import ActionEnum
from core.shared.domain.action_scopes import ACTION_SCOPES
from core.shared.domain.scope_enum import ScopeEnum

__all__ = [
    "Action",
    "ActionEnum",
    "ScopeEnum",
    "ACTION_SCOPES",
]
