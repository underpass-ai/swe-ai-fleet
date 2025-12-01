"""Constants for Task Valkey hash field names.

Centralizes all field names used in Valkey hash operations.
This prevents magic strings and makes refactoring easier.
"""


class TaskValkeyFields:
    """Constants for Task Valkey hash field names.

    Centralizes all field names used in Valkey hash operations.
    This prevents magic strings and makes refactoring easier.
    """

    TASK_ID = "task_id"
    STORY_ID = "story_id"  # REQUIRED - parent story (domain invariant)
    PLAN_ID = "plan_id"  # Optional - parent plan
    TITLE = "title"
    DESCRIPTION = "description"
    TYPE = "type"  # TaskType enum string value
    STATUS = "status"  # TaskStatus enum string value
    ASSIGNED_TO = "assigned_to"
    ESTIMATED_HOURS = "estimated_hours"
    PRIORITY = "priority"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"

