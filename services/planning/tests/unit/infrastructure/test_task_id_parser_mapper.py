"""Unit tests for TaskIdParserMapper."""

from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)
from planning.infrastructure.mappers.task_id_parser_mapper import TaskIdParserMapper


def test_parse_task_id_valid():
    """Test parsing valid task_id."""
    # Arrange
    task_id = "ceremony-abc123:story-ST-456:role-ARCHITECT"

    # Act
    ceremony_id, story_id, role = TaskIdParserMapper.parse_task_id(task_id)

    # Assert
    assert ceremony_id is not None
    assert isinstance(ceremony_id, BacklogReviewCeremonyId)
    assert ceremony_id.value == "abc123"

    assert story_id is not None
    assert isinstance(story_id, StoryId)
    assert story_id.value == "ST-456"

    assert role == BacklogReviewRole.ARCHITECT


def test_parse_task_id_all_roles():
    """Test parsing task_id with different roles."""
    roles = ["ARCHITECT", "QA", "DEVOPS"]

    for test_role in roles:
        task_id = f"ceremony-abc123:story-ST-456:role-{test_role}"
        ceremony_id, story_id, role = TaskIdParserMapper.parse_task_id(task_id)

        assert ceremony_id is not None
        assert story_id is not None
        assert role == BacklogReviewRole(test_role)


def test_parse_task_id_invalid_format_missing_parts():
    """Test parsing task_id with missing parts."""
    # Arrange
    task_id = "ceremony-abc123:story-ST-456"  # Missing role

    # Act
    ceremony_id, story_id, role = TaskIdParserMapper.parse_task_id(task_id)

    # Assert
    assert ceremony_id is None
    assert story_id is None
    assert role is None


def test_parse_task_id_invalid_format_extra_parts():
    """Test parsing task_id with extra parts."""
    # Arrange
    task_id = "ceremony-abc123:story-ST-456:role-ARCHITECT:extra"

    # Act
    ceremony_id, story_id, role = TaskIdParserMapper.parse_task_id(task_id)

    # Assert
    assert ceremony_id is None
    assert story_id is None
    assert role is None


def test_parse_task_id_missing_ceremony_prefix():
    """Test parsing task_id without ceremony- prefix."""
    # Arrange
    task_id = "abc123:story-ST-456:role-ARCHITECT"  # Missing "ceremony-"

    # Act
    ceremony_id, story_id, role = TaskIdParserMapper.parse_task_id(task_id)

    # Assert
    assert ceremony_id is None
    assert story_id is None
    assert role is None


def test_parse_task_id_missing_story_prefix():
    """Test parsing task_id without story- prefix."""
    # Arrange
    task_id = "ceremony-abc123:ST-456:role-ARCHITECT"  # Missing "story-"

    # Act
    ceremony_id, story_id, role = TaskIdParserMapper.parse_task_id(task_id)

    # Assert
    assert ceremony_id is None
    assert story_id is None
    assert role is None


def test_parse_task_id_missing_role_prefix():
    """Test parsing task_id without role- prefix."""
    # Arrange
    task_id = "ceremony-abc123:story-ST-456:ARCHITECT"  # Missing "role-"

    # Act
    ceremony_id, story_id, role = TaskIdParserMapper.parse_task_id(task_id)

    # Assert
    assert ceremony_id is None
    assert story_id is None
    assert role is None


def test_parse_task_id_empty_ceremony_id():
    """Test parsing task_id with empty ceremony ID."""
    # Arrange
    task_id = "ceremony-:story-ST-456:role-ARCHITECT"

    # Act
    ceremony_id, story_id, role = TaskIdParserMapper.parse_task_id(task_id)

    # Assert
    assert ceremony_id is None  # BacklogReviewCeremonyId validation should fail
    assert story_id is None
    assert role is None


def test_parse_task_id_empty_story_id():
    """Test parsing task_id with empty story ID."""
    # Arrange
    task_id = "ceremony-abc123:story-:role-ARCHITECT"

    # Act
    ceremony_id, story_id, role = TaskIdParserMapper.parse_task_id(task_id)

    # Assert
    assert ceremony_id is None  # StoryId validation should fail
    assert story_id is None
    assert role is None


def test_parse_task_id_complex_ids():
    """Test parsing task_id with complex IDs (UUIDs, etc.)."""
    # Arrange
    task_id = "ceremony-550e8400-e29b-41d4-a716-446655440000:story-ST-2024-001:role-QA"

    # Act
    ceremony_id, story_id, role = TaskIdParserMapper.parse_task_id(task_id)

    # Assert
    assert ceremony_id is not None
    assert ceremony_id.value == "550e8400-e29b-41d4-a716-446655440000"
    assert story_id is not None
    assert story_id.value == "ST-2024-001"
    assert role == BacklogReviewRole.QA


def test_parse_task_id_empty_string():
    """Test parsing empty task_id."""
    # Arrange
    task_id = ""

    # Act
    ceremony_id, story_id, role = TaskIdParserMapper.parse_task_id(task_id)

    # Assert
    assert ceremony_id is None
    assert story_id is None
    assert role is None

