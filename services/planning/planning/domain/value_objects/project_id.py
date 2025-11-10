"""ProjectId value object for Planning Service."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectId:
    """Value Object for Project identifier.

    Domain Invariant: ProjectId cannot be empty.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate ProjectId (fail-fast).

        Raises:
            ValueError: If project ID is empty or whitespace
        """
        if not self.value or not self.value.strip():
            raise ValueError("ProjectId cannot be empty")

    def __str__(self) -> str:
        """String representation.

        Returns:
            String value
        """
        return self.value

