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

        Raises:
            ValueError: If task_id is missing or invalid
        """
        import logging
        logger = logging.getLogger(__name__)

        # Extract task_id from entity (REQUIRED for backlog review ceremonies)
        task_id = entity.task_description_entity.task_id

        # Validate task_id is present and has correct format
        if not task_id or not task_id.strip():
            error_msg = (
                "❌ CRITICAL ERROR: task_id is MISSING in BacklogReviewDeliberationRequest! "
                "Backlog review ceremonies REQUIRE task_id in format 'ceremony-{id}:story-{id}:role-{role}'. "
                f"Entity: {entity}, task_description_entity: {entity.task_description_entity}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate task_id format for backlog review
        if not (task_id.startswith("ceremony-") and ":story-" in task_id and ":role-" in task_id):
            error_msg = (
                f"❌ CRITICAL ERROR: Invalid task_id format in BacklogReviewDeliberationRequest! "
                f"Expected format: 'ceremony-{{id}}:story-{{id}}:role-{{role}}', "
                f"got: '{task_id}'. "
                f"Entity: {entity}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"✅ BacklogReviewDeliberationMapper: Valid task_id found: {task_id}")

        # Extract story_id from task_id (format: "ceremony-{id}:story-{id}:role-{role}")
        story_id = BacklogReviewDeliberationMapper._extract_story_id_from_task_id(task_id)

        # Convert domain TaskConstraints to port TaskConstraints
        # Include original task_id in metadata so orchestrator can use it
        port_constraints = BacklogReviewDeliberationMapper._to_port_constraints(
            entity.constraints,
            story_id=story_id,
            task_id=task_id,  # Pass original task_id for orchestrator to use
        )

        logger.info(
            f"🔍 [TASK_ID_TRACE] BacklogReviewDeliberationMapper.to_deliberation_request: "
            f"ASSIGNING task_id='{task_id}' to DeliberationRequest"
        )
        return DeliberationRequest(
            task_id=task_id,  # REQUIRED for backlog review ceremonies (format: "ceremony-{id}:story-{id}:role-{role}")
            task_description=entity.task_description_entity.to_string(),
            role=entity.role.value,  # Convert enum to string for port
            constraints=port_constraints,
            rounds=1,
            num_agents=3,
        )

    @staticmethod
    def _extract_story_id_from_task_id(task_id: str) -> str:
        """
        Extract story_id from task_id format: "ceremony-{id}:story-{id}:role-{role}".

        Args:
            task_id: Task ID string

        Returns:
            Story ID string, or empty string if not found
        """
        try:
            # Split by ":" and find the part starting with "story-"
            parts = task_id.split(":")
            for part in parts:
                if part.startswith("story-"):
                    return part.replace("story-", "")
        except Exception:
            pass
        return ""

    @staticmethod
    def _to_port_constraints(
        domain_constraints: BacklogReviewTaskConstraints,
        story_id: str = "",
        task_id: str = "",
    ) -> TaskConstraints:
        """
        Convert domain BacklogReviewTaskConstraints to port TaskConstraints.

        Args:
            domain_constraints: Domain value object
            story_id: Story ID to include in constraints
            task_id: Original task_id to include in metadata

        Returns:
            Port TaskConstraints DTO
        """
        # Include task_id in metadata if provided
        metadata = dict(domain_constraints.metadata or {})
        if task_id:
            metadata["task_id"] = task_id

        return TaskConstraints(
            rubric=domain_constraints.rubric,
            requirements=domain_constraints.requirements,
            metadata=metadata,
            max_iterations=domain_constraints.max_iterations,
            timeout_seconds=domain_constraints.timeout_seconds,
            story_id=story_id,
        )

