"""Unit tests for TaskValkeyFields constants."""

from planning.infrastructure.mappers.task_valkey_fields import TaskValkeyFields


def test_task_valkey_fields_constants():
    """Test that all TaskValkeyFields constants are defined."""
    assert TaskValkeyFields.TASK_ID == "task_id"
    assert TaskValkeyFields.STORY_ID == "story_id"
    assert TaskValkeyFields.PLAN_ID == "plan_id"
    assert TaskValkeyFields.TITLE == "title"
    assert TaskValkeyFields.DESCRIPTION == "description"
    assert TaskValkeyFields.TYPE == "type"
    assert TaskValkeyFields.STATUS == "status"
    assert TaskValkeyFields.ASSIGNED_TO == "assigned_to"
    assert TaskValkeyFields.ESTIMATED_HOURS == "estimated_hours"
    assert TaskValkeyFields.PRIORITY == "priority"
    assert TaskValkeyFields.CREATED_AT == "created_at"
    assert TaskValkeyFields.UPDATED_AT == "updated_at"


def test_task_valkey_fields_all_strings():
    """Test that all TaskValkeyFields are strings."""
    fields = [
        TaskValkeyFields.TASK_ID,
        TaskValkeyFields.STORY_ID,
        TaskValkeyFields.PLAN_ID,
        TaskValkeyFields.TITLE,
        TaskValkeyFields.DESCRIPTION,
        TaskValkeyFields.TYPE,
        TaskValkeyFields.STATUS,
        TaskValkeyFields.ASSIGNED_TO,
        TaskValkeyFields.ESTIMATED_HOURS,
        TaskValkeyFields.PRIORITY,
        TaskValkeyFields.CREATED_AT,
        TaskValkeyFields.UPDATED_AT,
    ]

    for field in fields:
        assert isinstance(field, str)
        assert len(field) > 0

