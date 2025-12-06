"""BacklogReviewDeliberationRequest domain entity.

Represents a deliberation request for backlog review ceremonies.
Encapsulates the construction of deliberation requests with role-specific constraints.

Domain Entity:
- Uses only domain value objects (no ports, no DTOs)
- Converted to port DTOs by infrastructure mappers
"""

from dataclasses import dataclass

from planning.domain.entities.backlog_review_task_description import (
    BacklogReviewTaskDescription,
)
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)
from planning.domain.value_objects.review.task_constraints import (
    BacklogReviewTaskConstraints,
)


@dataclass(frozen=True)
class BacklogReviewDeliberationRequest:
    """
    Deliberation request for backlog review ceremonies.

    This entity encapsulates the construction of deliberation requests
    with role-specific constraints for backlog review. It provides
    builder methods to create requests with appropriate constraints
    for each review role (ARCHITECT, QA, DEVOPS).

    Domain Invariants:
    - task_description_entity must be valid BacklogReviewTaskDescription
    - role must be one of the valid review roles (ARCHITECT, QA, DEVOPS)
    - constraints must be valid BacklogReviewTaskConstraints

    Immutability: frozen=True ensures no mutation after creation.

    Note: This entity uses only domain value objects. Conversion to
    port DTOs (DeliberationRequest) is handled by infrastructure mappers.
    """

    task_description_entity: BacklogReviewTaskDescription
    role: BacklogReviewRole
    constraints: BacklogReviewTaskConstraints

    def __post_init__(self) -> None:
        """Validate deliberation request (fail-fast).

        Raises:
            ValueError: If any parameter is invalid
        """
        if not isinstance(self.task_description_entity, BacklogReviewTaskDescription):
            raise ValueError(
                "task_description_entity must be a BacklogReviewTaskDescription"
            )

        if not isinstance(self.role, BacklogReviewRole):
            raise ValueError(
                f"role must be a BacklogReviewRole enum, got {type(self.role)}"
            )

        if not isinstance(self.constraints, BacklogReviewTaskConstraints):
            raise ValueError(
                "constraints must be a BacklogReviewTaskConstraints"
            )

    @classmethod
    def build_for_role(
        cls,
        task_description_entity: BacklogReviewTaskDescription,
        role: BacklogReviewRole,
    ) -> "BacklogReviewDeliberationRequest":
        """
        Build deliberation request for a specific role (builder method).

        Creates a BacklogReviewDeliberationRequest with role-specific constraints.
        Each role has different evaluation criteria and requirements.

        Args:
            task_description_entity: Task description entity
            role: Review role (BacklogReviewRole enum)

        Returns:
            BacklogReviewDeliberationRequest with role-specific constraints

        Raises:
            ValueError: If role is invalid
        """
        if role == BacklogReviewRole.ARCHITECT:
            constraints = cls._build_architect_constraints()
        elif role == BacklogReviewRole.QA:
            constraints = cls._build_qa_constraints()
        elif role == BacklogReviewRole.DEVOPS:
            constraints = cls._build_devops_constraints()
        else:
            raise ValueError(
                f"Invalid role: {role}. Must be ARCHITECT, QA, or DEVOPS"
            )

        return cls(
            task_description_entity=task_description_entity,
            role=role,
            constraints=constraints,
        )

    @staticmethod
    def _build_architect_constraints() -> BacklogReviewTaskConstraints:
        """Build constraints for ARCHITECT role."""
        return BacklogReviewTaskConstraints(
            rubric="Evaluate technical feasibility, testability, infrastructure needs",
            requirements=(
                "Identify components needed",
                "List high-level tasks",
                "Estimate complexity",
            ),
            timeout_seconds=180,
        )

    @staticmethod
    def _build_qa_constraints() -> BacklogReviewTaskConstraints:
        """Build constraints for QA role."""
        return BacklogReviewTaskConstraints(
            rubric="Evaluate testability, acceptance criteria, edge cases",
            requirements=(
                "Identify test scenarios",
                "List acceptance criteria",
                "Estimate testing complexity",
            ),
            timeout_seconds=180,
        )

    @staticmethod
    def _build_devops_constraints() -> BacklogReviewTaskConstraints:
        """Build constraints for DEVOPS role."""
        return BacklogReviewTaskConstraints(
            rubric="Evaluate infrastructure needs, deployment requirements, monitoring",
            requirements=(
                "Identify infrastructure components",
                "List deployment steps",
                "Estimate operational complexity",
            ),
            timeout_seconds=180,
        )
