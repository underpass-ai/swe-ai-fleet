"""Mapper: Domain Story → Protobuf Story."""

from planning.domain import Story
from planning.gen import planning_pb2
from planning.infrastructure.mappers.datetime_formatter import format_datetime_iso


class StoryProtobufMapper:
    """
    Mapper: Convert domain Story to protobuf Story.

    Infrastructure Layer Responsibility:
    - Domain entities should not know about protobuf format
    - Conversions live in dedicated mappers (Hexagonal Architecture)
    """

    @staticmethod
    def to_protobuf(story: Story) -> planning_pb2.Story:
        """
        Convert domain Story to protobuf Story.

        Args:
            story: Domain Story entity.

        Returns:
            Protobuf Story message.
        """
        # Extract string values from Value Objects (protobuf requires primitives)
        # Ensure all values are primitive types (strings, ints) not Value Objects
        # Use str() to guarantee primitive string type and avoid any Value Object leakage
        # Pattern: Use constructor with kwargs (consistent with ResponseMapper._project_to_proto, etc.)
        return planning_pb2.Story(
            story_id=str(story.story_id.value),
            epic_id=str(story.epic_id.value),
            title=str(story.title.value),
            brief=str(story.brief.value),
            state=str(story.state.to_string()),
            dor_score=int(story.dor_score.value),
            created_by=str(story.created_by.value) if story.created_by is not None else "",
            created_at=format_datetime_iso(story.created_at),
            updated_at=format_datetime_iso(story.updated_at),
        )

