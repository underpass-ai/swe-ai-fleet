"""Mapper: Domain Story → Protobuf Story."""

from planning.gen import planning_pb2

from planning.domain import Story


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
        return planning_pb2.Story(
            story_id=story.story_id.value,
            title=story.title,
            brief=story.brief,
            state=story.state.to_string(),  # Tell, Don't Ask
            dor_score=story.dor_score.value,
            created_by=story.created_by,
            created_at=story.created_at.isoformat() + "Z",
            updated_at=story.updated_at.isoformat() + "Z",
        )

