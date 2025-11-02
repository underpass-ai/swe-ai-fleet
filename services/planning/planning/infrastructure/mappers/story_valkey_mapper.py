"""Mapper: Domain Story ↔ Valkey dict format."""

from datetime import datetime

from planning.domain import DORScore, Story, StoryId, StoryState, StoryStateEnum


class StoryValkeyMapper:
    """
    Mapper: Convert domain Story to/from Valkey dict format.

    Infrastructure Layer Responsibility:
    - Domain entities should not know about Redis hash format
    - Conversions live in dedicated mappers (Hexagonal Architecture)
    """

    @staticmethod
    def to_dict(story: Story) -> dict[str, str]:
        """
        Convert domain Story to Valkey hash dict.

        Args:
            story: Domain Story entity.

        Returns:
            Dict suitable for Redis HSET (all values as strings).
        """
        return {
            "story_id": story.story_id.value,
            "title": story.title,
            "brief": story.brief,
            "state": story.state.to_string(),  # Tell, Don't Ask
            "dor_score": str(story.dor_score.value),
            "created_by": story.created_by,
            "created_at": story.created_at.isoformat(),
            "updated_at": story.updated_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict[bytes, bytes]) -> Story:
        """
        Convert Valkey hash dict to domain Story.

        Args:
            data: Redis hash data (bytes keys and values).

        Returns:
            Domain Story entity.

        Raises:
            ValueError: If data is invalid or missing required fields.
        """
        if not data:
            raise ValueError("Cannot create Story from empty dict")

        return Story(
            story_id=StoryId(data[b"story_id"].decode("utf-8")),
            title=data[b"title"].decode("utf-8"),
            brief=data[b"brief"].decode("utf-8"),
            state=StoryState(StoryStateEnum(data[b"state"].decode("utf-8"))),
            dor_score=DORScore(int(data[b"dor_score"].decode("utf-8"))),
            created_by=data[b"created_by"].decode("utf-8"),
            created_at=datetime.fromisoformat(data[b"created_at"].decode("utf-8")),
            updated_at=datetime.fromisoformat(data[b"updated_at"].decode("utf-8")),
        )

