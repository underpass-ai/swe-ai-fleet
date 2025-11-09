"""ProjectId value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectId:
    """Value Object for Project identifier.

    ProjectId represents the unique identifier for a Project aggregate root.
    Projects are the top level of the work hierarchy.

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

    def to_string(self) -> str:
        """Convert to string representation.

        Explicit method following Tell, Don't Ask principle.

        Returns:
            String representation of project ID
        """
        return self.value

    def __str__(self) -> str:
        """String representation for compatibility.

        Returns:
            String representation
        """
        return self.to_string()

