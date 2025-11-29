"""Mapper: Domain Story ↔ Valkey dict format."""

from datetime import datetime

from planning.domain import (
    Brief,
    DORScore,
    Story,
    StoryId,
    StoryState,
    StoryStateEnum,
    Title,
    UserName,
)
from planning.domain.value_objects.identifiers.epic_id import EpicId


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
            "epic_id": story.epic_id.value,  # Parent reference (domain invariant)
            "title": story.title.value,
            "brief": story.brief.value,
            "state": story.state.to_string(),  # Tell, Don't Ask
            "dor_score": str(story.dor_score.value),
            "created_by": story.created_by.value,
            "created_at": story.created_at.isoformat(),
            "updated_at": story.updated_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict[str, str] | dict[bytes, bytes]) -> Story:
        """
        Convert Valkey hash dict to domain Story.

        Args:
            data: Redis hash data (string keys/values if decode_responses=True,
                  bytes keys/values if decode_responses=False).

        Returns:
            Domain Story entity.

        Raises:
            ValueError: If data is invalid or missing required fields.
        """
        if not data:
            raise ValueError("Cannot create Story from empty dict")

        # Handle both string and bytes keys (depending on decode_responses config)
        # ValkeyConfig has decode_responses=True, so strings are expected
        # But we handle both for robustness
        def get_str(key: str) -> str:
            """Get string value from dict, handling both string and bytes keys."""
            # Try string key first (decode_responses=True)
            if key in data:
                return str(data[key])
            # Try bytes key (decode_responses=False)
            key_bytes = key.encode("utf-8")
            if key_bytes in data:
                value = data[key_bytes]
                if isinstance(value, bytes):
                    return value.decode("utf-8")
                return str(value)
            raise ValueError(f"Missing required field: {key}")

        return Story(
            epic_id=EpicId(get_str("epic_id")),  # REQUIRED - domain invariant
            story_id=StoryId(get_str("story_id")),
            title=Title(get_str("title")),
            brief=Brief(get_str("brief")),
            state=StoryState(StoryStateEnum(get_str("state"))),
            dor_score=DORScore(int(get_str("dor_score"))),
            created_by=UserName(get_str("created_by")),
            created_at=datetime.fromisoformat(get_str("created_at")),
            updated_at=datetime.fromisoformat(get_str("updated_at")),
        )

