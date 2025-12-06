"""Mapper: BacklogReviewDeliberationRequest domain entity → OrchestratorPort DTOs.

Infrastructure Mapper:
- Converts domain entities → port DTOs
- Anti-corruption layer (domain → application)
- NO conversion methods in domain entities (DDD rule)
"""

from planning.application.ports.orchestrator_port import (
    DeliberationRequest,
    TaskConstraints,
)
from planning.domain.entities.backlog_review_deliberation_request import (
    BacklogReviewDeliberationRequest,
)
from planning.domain.value_objects.review.task_constraints import (
    BacklogReviewTaskConstraints,
)


class BacklogReviewDeliberationMapper:
    """
    Mapper: BacklogReviewDeliberationRequest → OrchestratorPort DTOs.

    Infrastructure Layer Responsibility:
    - Domain should not know about port DTOs
    - Conversion logic centralized in one place
    - Easy to version and evolve DTO structure
    """

    @staticmethod
    def to_deliberation_request(
        entity: BacklogReviewDeliberationRequest,
    ) -> DeliberationRequest:
        """
        Convert BacklogReviewDeliberationRequest to OrchestratorPort DeliberationRequest.

        Args:
            entity: Domain entity with role-specific constraints

        Returns:
            DeliberationRequest ready for OrchestratorPort.deliberate()
        """
        # Convert domain TaskConstraints to port TaskConstraints
        port_constraints = BacklogReviewDeliberationMapper._to_port_constraints(
            entity.constraints
        )

        return DeliberationRequest(
            task_description=entity.task_description_entity.to_string(),
            role=entity.role.value,  # Convert enum to string for port
            constraints=port_constraints,
            rounds=1,
            num_agents=3,
        )

    @staticmethod
    def _to_port_constraints(
        domain_constraints: BacklogReviewTaskConstraints,
    ) -> TaskConstraints:
        """
        Convert domain BacklogReviewTaskConstraints to port TaskConstraints.

        Args:
            domain_constraints: Domain value object

        Returns:
            Port TaskConstraints DTO
        """
        return TaskConstraints(
            rubric=domain_constraints.rubric,
            requirements=domain_constraints.requirements,
            metadata=domain_constraints.metadata,
            max_iterations=domain_constraints.max_iterations,
            timeout_seconds=domain_constraints.timeout_seconds,
        )

