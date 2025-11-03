"""RBAC domain entities for agents.

This module contains the Role-Based Access Control (RBAC) domain model
for the agents_and_tools bounded context.

Exports:
    - Action: Value object representing an action an agent can perform
    - Role: Value object representing an agent's role with allowed actions
    - RoleFactory: Factory for creating predefined roles
"""

from .action import Action, ActionEnum, ScopeEnum
from .role import Role, RoleEnum
from .role_factory import RoleFactory

__all__ = [
    "Action",
    "ActionEnum",
    "Role",
    "RoleEnum",
    "RoleFactory",
    "ScopeEnum",
]

