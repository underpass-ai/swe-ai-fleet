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
from planning.infrastructure.mappers.story_valkey_fields import StoryValkeyFields


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
            StoryValkeyFields.STORY_ID: story.story_id.value,
            StoryValkeyFields.EPIC_ID: story.epic_id.value,  # Parent reference (domain invariant)
            StoryValkeyFields.TITLE: story.title.value,
            StoryValkeyFields.BRIEF: story.brief.value,
            StoryValkeyFields.STATE: story.state.to_string(),  # Tell, Don't Ask
            StoryValkeyFields.DOR_SCORE: str(story.dor_score.value),
            StoryValkeyFields.CREATED_BY: story.created_by.value,
            StoryValkeyFields.CREATED_AT: story.created_at.isoformat(),
            StoryValkeyFields.UPDATED_AT: story.updated_at.isoformat(),
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
            # Check if data has string keys (decode_responses=True)
            sample_key = next(iter(data.keys())) if data else None
            if sample_key is not None and isinstance(sample_key, str):
                # dict[str, str] - try string key
                # Mypy cannot narrow the union type after runtime check
                if key in data:
                    value = data[key]  # type: ignore[index]
                    return str(value)
            # dict[bytes, bytes] - try bytes key
            # Mypy cannot narrow the union type after runtime check
            key_bytes = key.encode("utf-8")
            if key_bytes in data:
                value = data[key_bytes]  # type: ignore[index]
                if isinstance(value, bytes):
                    return value.decode("utf-8")
                return str(value)
            raise ValueError(f"Missing required field: {key}")

        return Story(
            epic_id=EpicId(get_str(StoryValkeyFields.EPIC_ID)),  # REQUIRED - domain invariant
            story_id=StoryId(get_str(StoryValkeyFields.STORY_ID)),
            title=Title(get_str(StoryValkeyFields.TITLE)),
            brief=Brief(get_str(StoryValkeyFields.BRIEF)),
            state=StoryState(StoryStateEnum(get_str(StoryValkeyFields.STATE))),
            dor_score=DORScore(int(get_str(StoryValkeyFields.DOR_SCORE))),
            created_by=UserName(get_str(StoryValkeyFields.CREATED_BY)),
            created_at=datetime.fromisoformat(get_str(StoryValkeyFields.CREATED_AT)),
            updated_at=datetime.fromisoformat(get_str(StoryValkeyFields.UPDATED_AT)),
        )

