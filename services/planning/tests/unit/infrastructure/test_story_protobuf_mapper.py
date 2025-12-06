"""Unit tests for StoryProtobufMapper."""

from datetime import UTC, datetime

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
from planning.gen import planning_pb2
from planning.infrastructure.mappers.story_protobuf_mapper import StoryProtobufMapper


def test_story_to_protobuf():
    """Test conversion from domain Story to protobuf Story."""
    now = datetime.now(UTC)

    story = Story(
        epic_id=EpicId("E-TEST-PROTOBUF-001"),
        story_id=StoryId("story-123"),
        title=Title("Test Story"),
        brief=Brief("Test brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(85),
        created_by=UserName("po-user"),
        created_at=now,
        updated_at=now,
    )

    pb_story = StoryProtobufMapper.to_protobuf(story)

    assert isinstance(pb_story, planning_pb2.Story)
    assert pb_story.story_id == "story-123"
    assert pb_story.epic_id == "E-TEST-PROTOBUF-001"  # Verify parent reference
    assert pb_story.title == "Test Story"
    assert pb_story.brief == "Test brief"
    assert pb_story.state == "DRAFT"
    assert pb_story.dor_score == 85
    assert pb_story.created_by == "po-user"
    assert pb_story.created_at.endswith("Z")
    assert pb_story.updated_at.endswith("Z")


def test_story_to_protobuf_with_different_states():
    """Test conversion for stories in different states."""
    now = datetime.now(UTC)
    epic_id = EpicId("E-TEST-PROTOBUF-STATES")

    for state_enum in [StoryStateEnum.DRAFT, StoryStateEnum.PO_REVIEW,
                       StoryStateEnum.ACCEPTED, StoryStateEnum.DONE]:
        story = Story(
            epic_id=epic_id,
            story_id=StoryId(f"story-{state_enum.value}"),
            title=Title("Test"),
            brief=Brief("Brief"),
            state=StoryState(state_enum),
            dor_score=DORScore(85),
            created_by=UserName("po"),
            created_at=now,
            updated_at=now,
        )

        pb_story = StoryProtobufMapper.to_protobuf(story)
        assert pb_story.state == state_enum.value

