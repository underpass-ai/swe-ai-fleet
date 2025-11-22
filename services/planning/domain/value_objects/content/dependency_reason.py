"""DependencyReason value object for task dependencies."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyReason:
    """Value Object for dependency reason.
    
    Explains why a task depends on another.
    Domain Invariant: Reason cannot be empty.
    Following DDD: No primitives - everything is a value object.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate DependencyReason (fail-fast).
        
        Raises:
            ValueError: If reason is empty or whitespace
        """
        if not self.value or not self.value.strip():
            raise ValueError("DependencyReason cannot be empty")

    def __str__(self) -> str:
        """String representation.
        
        Returns:
            String value
        """
        return self.value

