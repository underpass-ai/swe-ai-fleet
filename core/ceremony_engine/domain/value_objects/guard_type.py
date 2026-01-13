"""GuardType: Enumeration of guard types."""

from enum import Enum


class GuardType(str, Enum):
    """
    Enumeration of guard types.

    Guard types define how a guard is evaluated:
    - AUTOMATED: Evaluated automatically (expression/condition)
    - HUMAN: Requires human decision/approval
    """

    AUTOMATED = "automated"
    HUMAN = "human"
