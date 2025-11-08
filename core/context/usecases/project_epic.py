# core/context/usecases/project_epic.py
from dataclasses import dataclass
from typing import Any

from core.context.domain.epic import Epic
from core.context.infrastructure.mappers.epic_mapper import EpicMapper
from core.context.ports.graph_command_port import GraphCommandPort


@dataclass
class ProjectEpicUseCase:
    """Use case for creating/updating Epics in Neo4j.

    This use case follows Hexagonal Architecture:
    - Receives event payload (dict)
    - Uses mapper to convert to domain entity
    - Calls port with domain entity (NO primitives)
    """

    writer: GraphCommandPort

    def execute(self, payload: dict[str, Any]) -> None:
        """Execute epic projection.

        Args:
            payload: Event payload with {epic_id, title, description?, status?}
        """
        # Use mapper to convert payload to domain entity
        epic = EpicMapper.from_event_payload(payload)

        # Save epic entity to Neo4j
        self.writer.save_epic(epic)

