"""Constants for Story Valkey hash field names.

Centralizes all field names used in Valkey hash operations.
This prevents magic strings and makes refactoring easier.
"""


class StoryValkeyFields:
    """Constants for Story Valkey hash field names.

    Centralizes all field names used in Valkey hash operations.
    This prevents magic strings and makes refactoring easier.
    """

    STORY_ID = "story_id"
    EPIC_ID = "epic_id"
    TITLE = "title"
    BRIEF = "brief"
    STATE = "state"
    DOR_SCORE = "dor_score"
    CREATED_BY = "created_by"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"

