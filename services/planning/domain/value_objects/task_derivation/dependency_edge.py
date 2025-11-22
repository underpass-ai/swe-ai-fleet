"""DependencyEdge value object for task dependencies.

Value Object (DDD):
- Defined by its values, not identity
- Immutable (frozen=True)
- NO primitives - all typed with VOs
"""

from dataclasses import dataclass

from ..content.dependency_reason import DependencyReason
from ..identifiers.task_id import TaskId


@dataclass(frozen=True)
class DependencyEdge:
    """Dependency edge between two tasks.
    
    Immutable representation of a dependency relationship.
    NO serialization methods (use mappers in infrastructure).
    
    Following DDD:
    - Value object (no identity)
    - Immutable
    - NO primitives - all fields are Value Objects
    - Fail-fast validation in __post_init__
    """

    from_task_id: TaskId
    to_task_id: TaskId
    reason: DependencyReason

    def __post_init__(self) -> None:
        """Validate dependency edge (fail-fast).
        
        Note: Individual VOs already validate themselves.
        This validates business rules.
        
        Raises:
            ValueError: If validation fails
        """
        # Individual VOs validate themselves (TaskId, DependencyReason)

        # Business rule: Cannot create self-dependency
        if self.from_task_id.value == self.to_task_id.value:
            raise ValueError(
                f"Cannot create self-dependency: {self.from_task_id.value}"
            )

