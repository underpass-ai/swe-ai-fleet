"""Unit tests for gRPC server (PlanningServiceServicer)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from grpc.aio import ServicerContext
from planning.gen import planning_pb2

from planning.application.usecases import InvalidTransitionError, StoryNotFoundError
from planning.domain import DORScore, Story, StoryId, StoryState, StoryStateEnum
from planning.domain.value_objects.identifiers.decision_id import DecisionId
from planning.domain.value_objects.identifiers.epic_id import EpicId
from server import PlanningServiceServicer


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    context = MagicMock(spec=ServicerContext)
    context.set_code = MagicMock()
    context.set_details = MagicMock()
    return context


@pytest.fixture
def sample_story():
    """Create sample story for tests."""
    now = datetime.now(UTC)
    return Story(
        epic_id=EpicId("E-TEST-SERVER"),
        story_id=StoryId("story-123"),
        title="Test Story",
        brief="Test brief",
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by="po-user",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def servicer():
    """Create servicer with mocked use cases (15 + storage)."""
    # Project use cases
    create_project_uc = AsyncMock()
    get_project_uc = AsyncMock()
    list_projects_uc = AsyncMock()
    # Epic use cases
    create_epic_uc = AsyncMock()
    get_epic_uc = AsyncMock()
    list_epics_uc = AsyncMock()
    # Story use cases
    create_story_uc = AsyncMock()
    list_uc = AsyncMock()
    transition_uc = AsyncMock()
    # Task use cases
    create_task_uc = AsyncMock()
    get_task_uc = AsyncMock()
    list_tasks_uc = AsyncMock()
    # Decision use cases
    approve_uc = AsyncMock()
    reject_uc = AsyncMock()
    # Storage
    storage = AsyncMock()

    return PlanningServiceServicer(
        # Project
        create_project_uc=create_project_uc,
        get_project_uc=get_project_uc,
        list_projects_uc=list_projects_uc,
        # Epic
        create_epic_uc=create_epic_uc,
        get_epic_uc=get_epic_uc,
        list_epics_uc=list_epics_uc,
        # Story
        create_story_uc=create_story_uc,
        list_stories_uc=list_uc,
        transition_story_uc=transition_uc,
        # Task
        create_task_uc=create_task_uc,
        get_task_uc=get_task_uc,
        list_tasks_uc=list_tasks_uc,
        # Decision
        approve_decision_uc=approve_uc,
        reject_decision_uc=reject_uc,
        # Storage
        storage=storage,
    )


@pytest.mark.asyncio
async def test_create_story_success(servicer, mock_context, sample_story):
    """Test CreateStory with successful creation."""
    servicer.create_story_uc.execute.return_value = sample_story

    request = planning_pb2.CreateStoryRequest(
        epic_id="EPIC-TEST-001",
        title="Test Story",
        brief="Test brief",
        created_by="po-user",
    )

    response = await servicer.CreateStory(request, mock_context)

    assert response.success is True
    assert "Story created" in response.message
    assert response.story.story_id == "story-123"
    assert response.story.title == "Test Story"

    # Verify use case was called with epic_id
    call_kwargs = servicer.create_story_uc.execute.call_args.kwargs
    assert call_kwargs["epic_id"].value == "EPIC-TEST-001"
    assert call_kwargs["title"] == "Test Story"
    assert call_kwargs["brief"] == "Test brief"
    assert call_kwargs["created_by"] == "po-user"


@pytest.mark.asyncio
async def test_create_story_validation_error(servicer, mock_context):
    """Test CreateStory with validation error."""
    servicer.create_story_uc.execute.side_effect = ValueError("Title cannot be empty")

    request = planning_pb2.CreateStoryRequest(
        epic_id="EPIC-TEST-001",
        title="",
        brief="Brief",
        created_by="po-user",
    )

    response = await servicer.CreateStory(request, mock_context)

    assert response.success is False
    assert "Title cannot be empty" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_create_story_internal_error(servicer, mock_context):
    """Test CreateStory with internal error."""
    servicer.create_story_uc.execute.side_effect = Exception("Database error")

    request = planning_pb2.CreateStoryRequest(
        epic_id="EPIC-TEST-001",
        title="Title",
        brief="Brief",
        created_by="po-user",
    )

    response = await servicer.CreateStory(request, mock_context)

    assert response.success is False
    assert "Internal error" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)


@pytest.mark.asyncio
async def test_list_stories_success(servicer, mock_context, sample_story):
    """Test ListStories with successful retrieval."""
    servicer.list_stories_uc.execute.return_value = [sample_story]

    request = planning_pb2.ListStoriesRequest(
        state_filter="DRAFT",
        limit=10,
        offset=0,
    )

    response = await servicer.ListStories(request, mock_context)

    assert response.success is True
    assert response.total_count == 1
    assert len(response.stories) == 1
    assert response.stories[0].story_id == "story-123"


@pytest.mark.asyncio
async def test_list_stories_no_filter(servicer, mock_context, sample_story):
    """Test ListStories without state filter."""
    servicer.list_stories_uc.execute.return_value = [sample_story]

    request = planning_pb2.ListStoriesRequest()

    response = await servicer.ListStories(request, mock_context)

    assert response.success is True
    assert response.total_count == 1

    # Verify state_filter was None
    call_kwargs = servicer.list_stories_uc.execute.call_args.kwargs
    assert call_kwargs['state_filter'] is None


@pytest.mark.asyncio
async def test_list_stories_error(servicer, mock_context):
    """Test ListStories with error."""
    servicer.list_stories_uc.execute.side_effect = Exception("Query failed")

    request = planning_pb2.ListStoriesRequest()

    response = await servicer.ListStories(request, mock_context)

    assert response.success is False
    assert "Error" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)


@pytest.mark.asyncio
async def test_transition_story_success(servicer, mock_context, sample_story):
    """Test TransitionStory with successful transition."""
    transitioned_story = Story(
        epic_id=sample_story.epic_id,  # REQUIRED - preserve parent reference
        story_id=sample_story.story_id,
        title=sample_story.title,
        brief=sample_story.brief,
        state=StoryState(StoryStateEnum.PO_REVIEW),
        dor_score=sample_story.dor_score,
        created_by=sample_story.created_by,
        created_at=sample_story.created_at,
        updated_at=datetime.now(UTC),
    )
    servicer.transition_story_uc.execute.return_value = transitioned_story

    request = planning_pb2.TransitionStoryRequest(
        story_id="story-123",
        target_state="PO_REVIEW",
        transitioned_by="po-user",
    )

    response = await servicer.TransitionStory(request, mock_context)

    assert response.success is True
    assert "transitioned" in response.message
    assert response.story.state == "PO_REVIEW"


@pytest.mark.asyncio
async def test_transition_story_not_found(servicer, mock_context):
    """Test TransitionStory when story doesn't exist."""
    servicer.transition_story_uc.execute.side_effect = StoryNotFoundError("Story not found")

    request = planning_pb2.TransitionStoryRequest(
        story_id="nonexistent",
        target_state="PO_REVIEW",
        transitioned_by="po-user",
    )

    response = await servicer.TransitionStory(request, mock_context)

    assert response.success is False
    assert "not found" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.NOT_FOUND)


@pytest.mark.asyncio
async def test_transition_story_invalid_transition(servicer, mock_context):
    """Test TransitionStory with invalid FSM transition."""
    servicer.transition_story_uc.execute.side_effect = InvalidTransitionError(
        "Invalid transition: DRAFT → DONE"
    )

    request = planning_pb2.TransitionStoryRequest(
        story_id="story-123",
        target_state="DONE",
        transitioned_by="po-user",
    )

    response = await servicer.TransitionStory(request, mock_context)

    assert response.success is False
    assert "Invalid transition" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.FAILED_PRECONDITION)


@pytest.mark.asyncio
async def test_approve_decision_success(servicer, mock_context):
    """Test ApproveDecision with successful approval."""
    request = planning_pb2.ApproveDecisionRequest(
        story_id="story-123",
        decision_id="decision-456",
        approved_by="po-user",
        comment="Looks good",
    )

    response = await servicer.ApproveDecision(request, mock_context)

    assert response.success is True
    assert "approved" in response.message

    servicer.approve_decision_uc.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_approve_decision_no_comment(servicer, mock_context):
    """Test ApproveDecision without optional comment."""
    request = planning_pb2.ApproveDecisionRequest(
        story_id="story-123",
        decision_id="decision-456",
        approved_by="po-user",
    )

    response = await servicer.ApproveDecision(request, mock_context)

    assert response.success is True
    servicer.approve_decision_uc.execute.assert_awaited_once()
    # Handler no longer passes comment parameter


@pytest.mark.asyncio
async def test_approve_decision_validation_error(servicer, mock_context):
    """Test ApproveDecision with validation error."""
    servicer.approve_decision_uc.execute.side_effect = ValueError("Invalid decision_id")

    request = planning_pb2.ApproveDecisionRequest(
        story_id="story-123",
        decision_id="",
        approved_by="po-user",
    )

    response = await servicer.ApproveDecision(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_reject_decision_success(servicer, mock_context):
    """Test RejectDecision with successful rejection."""
    request = planning_pb2.RejectDecisionRequest(
        story_id="story-123",
        decision_id="decision-456",
        rejected_by="po-user",
        reason="Needs revision",
    )

    response = await servicer.RejectDecision(request, mock_context)

    assert response.success is True
    assert "rejected" in response.message

    servicer.reject_decision_uc.execute.assert_awaited_once_with(
        story_id=StoryId("story-123"),
        decision_id=DecisionId("decision-456"),
        rejected_by="po-user",
        reason="Needs revision",
    )


@pytest.mark.asyncio
async def test_reject_decision_validation_error(servicer, mock_context):
    """Test RejectDecision with validation error."""
    servicer.reject_decision_uc.execute.side_effect = ValueError("Reason required")

    request = planning_pb2.RejectDecisionRequest(
        story_id="story-123",
        decision_id="decision-456",
        rejected_by="po-user",
        reason="",
    )

    response = await servicer.RejectDecision(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_get_story_success(servicer, mock_context, sample_story):
    """Test GetStory with successful retrieval."""
    servicer.storage.get_story.return_value = sample_story

    request = planning_pb2.GetStoryRequest(story_id="story-123")

    response = await servicer.GetStory(request, mock_context)

    assert response.story_id == "story-123"
    assert response.title == "Test Story"

    servicer.storage.get_story.assert_awaited_once_with(StoryId("story-123"))


@pytest.mark.asyncio
async def test_get_story_not_found(servicer, mock_context):
    """Test GetStory when story doesn't exist."""
    servicer.storage.get_story.return_value = None

    request = planning_pb2.GetStoryRequest(story_id="nonexistent")

    response = await servicer.GetStory(request, mock_context)

    # Returns empty Story protobuf
    assert response.story_id == ""
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.NOT_FOUND)


@pytest.mark.asyncio
async def test_get_story_error(servicer, mock_context):
    """Test GetStory with error."""
    storage_mock = AsyncMock()
    storage_mock.get_story.side_effect = Exception("Database error")
    servicer.list_stories_uc.storage = storage_mock

    request = planning_pb2.GetStoryRequest(story_id="story-123")

    response = await servicer.GetStory(request, mock_context)

    assert response.story_id == ""
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)


# Mapper conversion is now tested in test_story_protobuf_mapper.py
# This test is no longer needed as _story_to_pb was moved to StoryProtobufMapper

