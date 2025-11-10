"""Unit tests for StoryList value object."""

from datetime import UTC, datetime

import pytest

from planning.domain import DORScore, Story, StoryId, StoryList, StoryState, StoryStateEnum
from planning.domain.value_objects.epic_id import EpicId


@pytest.fixture
def sample_stories():
    """Create sample stories for tests."""
    now = datetime.now(UTC)
    epic_id = EpicId("E-TEST-FIXTURE")  # Common epic for all test stories
    return [
        Story(
            epic_id=epic_id,
            story_id=StoryId("story-1"),
            title="Story 1",
            brief="Brief 1",
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(50),
            created_by="po",
            created_at=now,
            updated_at=now,
        ),
        Story(
            epic_id=epic_id,
            story_id=StoryId("story-2"),
            title="Story 2",
            brief="Brief 2",
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(85),
            created_by="po",
            created_at=now,
            updated_at=now,
        ),
        Story(
            epic_id=epic_id,
            story_id=StoryId("story-3"),
            title="Story 3",
            brief="Brief 3",
            state=StoryState(StoryStateEnum.PO_REVIEW),
            dor_score=DORScore(90),
            created_by="po",
            created_at=now,
            updated_at=now,
        ),
    ]


def test_story_list_from_list(sample_stories):
    """Test creating StoryList from list."""
    story_list = StoryList.from_list(sample_stories)

    assert story_list.count() == 3
    assert len(story_list) == 3
    assert not story_list.is_empty()


def test_story_list_empty():
    """Test creating empty StoryList."""
    story_list = StoryList.empty()

    assert story_list.count() == 0
    assert len(story_list) == 0
    assert story_list.is_empty()


def test_story_list_is_frozen(sample_stories):
    """Test that StoryList is immutable."""
    story_list = StoryList.from_list(sample_stories)

    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        story_list.stories = ()  # type: ignore


def test_story_list_iteration(sample_stories):
    """Test iterating over StoryList."""
    story_list = StoryList.from_list(sample_stories)

    count = 0
    for story in story_list:
        assert isinstance(story, Story)
        count += 1

    assert count == 3


def test_story_list_indexing(sample_stories):
    """Test accessing stories by index."""
    story_list = StoryList.from_list(sample_stories)

    assert story_list[0].story_id.value == "story-1"
    assert story_list[1].story_id.value == "story-2"
    assert story_list[2].story_id.value == "story-3"


def test_story_list_filter_by_state(sample_stories):
    """Test filtering stories by state."""
    story_list = StoryList.from_list(sample_stories)

    draft_stories = story_list.filter_by_state(StoryState(StoryStateEnum.DRAFT))

    assert draft_stories.count() == 2
    assert draft_stories[0].state.value == StoryStateEnum.DRAFT
    assert draft_stories[1].state.value == StoryStateEnum.DRAFT


def test_story_list_filter_by_state_no_matches(sample_stories):
    """Test filtering with no matches."""
    story_list = StoryList.from_list(sample_stories)

    done_stories = story_list.filter_by_state(StoryState(StoryStateEnum.DONE))

    assert done_stories.count() == 0
    assert done_stories.is_empty()


def test_story_list_convert_to_list_via_builtin(sample_stories):
    """Test converting StoryList to list using list() builtin."""
    story_list = StoryList.from_list(sample_stories)

    result = list(story_list)  # Uses __iter__

    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0].story_id.value == "story-1"


def test_story_list_str_representation():
    """Test string representation."""
    story_list = StoryList.empty()
    assert "0" in str(story_list)

    story_list = StoryList.from_list([
        Story(
            epic_id=EpicId("E-TEST-STR"),
            story_id=StoryId("s-1"),
            title="T",
            brief="B",
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(50),
            created_by="po",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    ])
    assert "1" in str(story_list)


def test_story_list_immutable_tuple():
    """Test that stories are stored as immutable tuple."""
    stories = [
        Story(
            epic_id=EpicId("E-TEST-IMM"),
            story_id=StoryId("s-1"),
            title="T",
            brief="B",
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(50),
            created_by="po",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    ]

    story_list = StoryList.from_list(stories)

    # Modifying original list should not affect StoryList
    stories.clear()
    assert story_list.count() == 1

