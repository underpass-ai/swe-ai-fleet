"""Integration contract with Planning Service.

Defines constants and contracts for Planning Service bounded context integration.
Following DDD bounded context isolation principles.
"""


class PlanningStoryState:
    """Planning Service story states (integration contract).

    Domain knowledge: These are Planning Service's StoryStateEnum values.
    Defined here to avoid coupling between bounded contexts.

    Anti-Corruption Layer (ACL):
    - Cannot import from Planning Service (bounded context isolation)
    - Values MUST match Planning Service's StoryStateEnum
    - If Planning Service changes these values, this contract must be updated

    Following DDD Shared Kernel alternative:
    - Instead of shared code, we document the contract
    - Each bounded context has its own representation
    - Changes require explicit coordination

    Used by:
    - PlanningEventsConsumer (filters events by state)
    - Integration tests (validate contract)
    """

    # Story lifecycle states (subset relevant to Workflow Service)
    READY_FOR_EXECUTION = "READY_FOR_EXECUTION"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"

