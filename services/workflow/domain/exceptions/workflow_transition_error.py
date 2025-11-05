"""Workflow transition error.

Domain exception raised when a workflow transition violates FSM rules.
Following Domain-Driven Design principles.
"""


class WorkflowTransitionError(Exception):
    """Raised when a workflow transition is not allowed.

    Examples:
    - Role not allowed for action in current state
    - Action not defined for current state
    - Transition violates FSM guards

    This is a domain exception (business rule violation).
    """

