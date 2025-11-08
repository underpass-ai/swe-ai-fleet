# core/context/usecases/project_plan_version.py
from dataclasses import dataclass
from typing import Any

from core.context.domain.plan_version import PlanVersion
from core.context.infrastructure.mappers.plan_version_mapper import PlanVersionMapper
from core.context.ports.graph_command_port import GraphCommandPort


@dataclass
class ProjectPlanVersionUseCase:
    """Use case for creating/updating PlanVersions in Neo4j.

    This use case follows Hexagonal Architecture:
    - Receives event payload (dict)
    - Uses mapper to convert to domain entity
    - Calls port with domain entity (NO primitives)
    """

    writer: GraphCommandPort

    def execute(self, payload: dict[str, Any]) -> None:
        """Execute plan version projection.

        Args:
            payload: Event payload with {story_id, plan_id, version}
        """
        # Use mapper to convert payload to domain entity
        plan_version = PlanVersionMapper.from_event_payload(payload)

        # Save plan version entity
        self.writer.save_plan_version(plan_version)

        # Create relationship to story
        relationship = plan_version.get_relationship_to_story()
        self.writer.create_relationship(relationship)
