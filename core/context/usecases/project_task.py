# core/context/usecases/project_task.py
from dataclasses import dataclass
from typing import Any

from core.context.infrastructure.mappers.task_mapper import TaskMapper
from core.context.ports.graph_command_port import GraphCommandPort


@dataclass
class ProjectTaskUseCase:
    """Use case for creating/updating Tasks in Neo4j (formerly ProjectSubtaskUseCase).

    This use case follows Hexagonal Architecture:
    - Receives event payload (dict)
    - Uses mapper to convert to domain entity
    - Calls port with domain entity (NO primitives)
    """

    writer: GraphCommandPort

    def execute(self, payload: dict[str, Any]) -> None:
        """Execute task projection.

        Args:
            payload: Event payload with {plan_id, task_id, title?, type?}
        """
        # Use mapper to convert payload to domain entity
        task = TaskMapper.from_event_payload(payload)

        # Create relationship to plan
        relationship = task.get_relationship_to_plan()
        self.writer.create_relationship(relationship)
