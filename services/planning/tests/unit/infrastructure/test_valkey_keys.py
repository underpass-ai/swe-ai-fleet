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


def test_valkey_keys_stories_by_epic():
    """Test stories_by_epic key generation."""
    from planning.domain.value_objects.identifiers.epic_id import EpicId

    epic_id = EpicId("E-123")

    key = ValkeyKeys.stories_by_epic(epic_id)

    assert key == "planning:stories:epic:E-123"
    assert key.startswith("planning:")
    assert "E-123" in key


def test_valkey_keys_projects_by_status():
    """Test projects_by_status key generation."""
    key = ValkeyKeys.projects_by_status("active")

    assert key == "planning:projects:status:active"
    assert key.startswith("planning:")
    assert "active" in key


def test_valkey_keys_epic_hash():
    """Test epic hash key generation."""
    from planning.domain.value_objects.identifiers.epic_id import EpicId

    epic_id = EpicId("E-123")

    key = ValkeyKeys.epic_hash(epic_id)

    assert key == "planning:epic:E-123"
    assert key.startswith("planning:")
    assert "E-123" in key


def test_valkey_keys_all_epics():
    """Test all epics set key generation."""
    key = ValkeyKeys.all_epics()

    assert key == "planning:epics:all"
    assert key.startswith("planning:")


def test_valkey_keys_epics_by_project():
    """Test epics_by_project key generation."""
    from planning.domain.value_objects.identifiers.project_id import ProjectId

    project_id = ProjectId("PROJ-123")

    key = ValkeyKeys.epics_by_project(project_id)

    assert key == "planning:epics:project:PROJ-123"
    assert key.startswith("planning:")
    assert "PROJ-123" in key


def test_valkey_keys_task_hash():
    """Test task hash key generation."""
    from planning.domain.value_objects.identifiers.task_id import TaskId

    task_id = TaskId("T-123")

    key = ValkeyKeys.task_hash(task_id)

    assert key == "planning:task:T-123"
    assert key.startswith("planning:")
    assert "T-123" in key


def test_valkey_keys_all_tasks():
    """Test all tasks set key generation."""
    key = ValkeyKeys.all_tasks()

    assert key == "planning:tasks:all"
    assert key.startswith("planning:")


def test_valkey_keys_tasks_by_story():
    """Test tasks_by_story key generation."""
    story_id = StoryId("story-123")

    key = ValkeyKeys.tasks_by_story(story_id)

    assert key == "planning:tasks:story:story-123"
    assert key.startswith("planning:")
    assert "story-123" in key


def test_valkey_keys_tasks_by_plan():
    """Test tasks_by_plan key generation."""
    from planning.domain.value_objects.identifiers.plan_id import PlanId

    plan_id = PlanId("PL-123")

    key = ValkeyKeys.tasks_by_plan(plan_id)

    assert key == "planning:tasks:plan:PL-123"
    assert key.startswith("planning:")
    assert "PL-123" in key


def test_valkey_keys_ceremony_story_po_approval():
    """Test ceremony_story_po_approval key generation."""
    from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
        BacklogReviewCeremonyId,
    )

    ceremony_id = BacklogReviewCeremonyId("BRC-123")
    story_id = StoryId("ST-456")

    key = ValkeyKeys.ceremony_story_po_approval(ceremony_id, story_id)

    assert key == "planning:ceremony:BRC-123:story:ST-456:po_approval"
    assert key.startswith("planning:")
    assert "BRC-123" in key
    assert "ST-456" in key
    assert key.endswith(":po_approval")

