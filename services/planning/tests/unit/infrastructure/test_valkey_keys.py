"""Unit tests for ValkeyKeys (Redis key schema)."""

from planning.domain import StoryId, StoryState, StoryStateEnum
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.infrastructure.adapters.valkey_keys import ValkeyKeys


def test_valkey_keys_story_hash():
    """Test story hash key generation."""
    story_id = StoryId("story-123")

    key = ValkeyKeys.story_hash(story_id)

    assert key == "planning:story:story-123"
    assert key.startswith("planning:")
    assert "story-123" in key


def test_valkey_keys_story_state():
    """Test story state key generation."""
    story_id = StoryId("story-456")

    key = ValkeyKeys.story_state(story_id)

    assert key == "planning:story:story-456:state"
    assert key.endswith(":state")
    assert "story-456" in key


def test_valkey_keys_all_stories():
    """Test all stories set key generation."""
    key = ValkeyKeys.all_stories()

    assert key == "planning:stories:all"
    assert key.startswith("planning:")


def test_valkey_keys_stories_by_state():
    """Test stories by state set key generation."""
    state = StoryState(StoryStateEnum.IN_PROGRESS)

    key = ValkeyKeys.stories_by_state(state)

    assert key == "planning:stories:state:IN_PROGRESS"
    assert "IN_PROGRESS" in key
    assert key.startswith("planning:stories:state:")


def test_valkey_keys_stories_by_state_various_states():
    """Test key generation for different states."""
    states_and_keys = [
        (StoryStateEnum.DRAFT, "planning:stories:state:DRAFT"),
        (StoryStateEnum.PO_REVIEW, "planning:stories:state:PO_REVIEW"),
        (StoryStateEnum.DONE, "planning:stories:state:DONE"),
        (StoryStateEnum.ARCHIVED, "planning:stories:state:ARCHIVED"),
    ]

    for state_enum, expected_key in states_and_keys:
        state = StoryState(state_enum)
        key = ValkeyKeys.stories_by_state(state)
        assert key == expected_key


def test_valkey_keys_namespace_consistency():
    """Test that all keys use consistent namespace."""
    story_id = StoryId("test-id")
    state = StoryState(StoryStateEnum.DRAFT)

    keys = [
        ValkeyKeys.story_hash(story_id),
        ValkeyKeys.story_state(story_id),
        ValkeyKeys.all_stories(),
        ValkeyKeys.stories_by_state(state),
    ]

    for key in keys:
        assert key.startswith("planning:")


def test_valkey_keys_no_key_collision():
    """Test that different keys don't collide."""
    story_id = StoryId("test-123")
    state = StoryState(StoryStateEnum.DRAFT)

    keys = {
        ValkeyKeys.story_hash(story_id),
        ValkeyKeys.story_state(story_id),
        ValkeyKeys.all_stories(),
        ValkeyKeys.stories_by_state(state),
    }

    # All keys should be unique
    assert len(keys) == 4


def test_valkey_keys_special_characters_in_story_id():
    """Test key generation with special characters in story ID."""
    # Story IDs with hyphens, underscores
    story_id = StoryId("story-test_123")

    hash_key = ValkeyKeys.story_hash(story_id)
    state_key = ValkeyKeys.story_state(story_id)

    assert "story-test_123" in hash_key
    assert "story-test_123" in state_key


def test_valkey_keys_project_hash():
    """Test project hash key generation."""
    project_id = ProjectId("PROJ-123")

    key = ValkeyKeys.project_hash(project_id)

    assert key == "planning:project:PROJ-123"
    assert key.startswith("planning:")
    assert "PROJ-123" in key


def test_valkey_keys_all_projects():
    """Test all projects set key generation."""
    key = ValkeyKeys.all_projects()

    assert key == "planning:projects:all"
    assert key.startswith("planning:")


def test_valkey_keys_project_namespace_consistency():
    """Test that project keys use consistent namespace."""
    project_id = ProjectId("PROJ-TEST")

    keys = [
        ValkeyKeys.project_hash(project_id),
        ValkeyKeys.all_projects(),
    ]

    for key in keys:
        assert key.startswith("planning:")


def test_valkey_keys_no_project_story_key_collision():
    """Test that project keys don't collide with story keys."""
    project_id = ProjectId("PROJ-123")
    story_id = StoryId("story-123")
    state = StoryState(StoryStateEnum.DRAFT)

    project_keys = {
        ValkeyKeys.project_hash(project_id),
        ValkeyKeys.all_projects(),
    }

    story_keys = {
        ValkeyKeys.story_hash(story_id),
        ValkeyKeys.story_state(story_id),
        ValkeyKeys.all_stories(),
        ValkeyKeys.stories_by_state(state),
    }

    # No intersection between project and story keys
    assert project_keys.isdisjoint(story_keys)


def test_valkey_keys_project_special_characters():
    """Test key generation with special characters in project ID."""
    project_id = ProjectId("PROJ-test_123-456")

    hash_key = ValkeyKeys.project_hash(project_id)

    assert "PROJ-test_123-456" in hash_key

