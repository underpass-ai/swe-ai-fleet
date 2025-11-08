# core/context/usecases/project_story.py (renamed from project_case.py)
from dataclasses import dataclass
from typing import Any

from core.context.infrastructure.mappers.story_mapper import StoryMapper
from core.context.ports.graph_command_port import GraphCommandPort


@dataclass
class ProjectStoryUseCase:
    """Use case for creating/updating Stories in Neo4j.

    Formerly ProjectCaseUseCase (renamed for consistency with Planning Service).

    This use case follows Hexagonal Architecture:
    - Receives event payload (dict)
    - Uses mapper to convert to domain entity
    - Calls port with domain entity (NO primitives)
    """

    writer: GraphCommandPort

    def execute(self, payload: dict[str, Any]) -> None:
        """Execute story projection.

        Args:
            payload: Event payload with {story_id, name?}
        """
        # Use mapper to convert payload to domain entity
        story = StoryMapper.from_event_payload(payload)

        # Pass domain entity to port (port handles persistence details)
        self.writer.save_story(story)
