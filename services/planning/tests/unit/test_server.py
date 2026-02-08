"""Unit tests for gRPC server (PlanningServiceServicer)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from grpc.aio import ServicerContext
from planning.application.usecases import InvalidTransitionError, StoryNotFoundError
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
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.entities.plan import Plan
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.decision_id import DecisionId
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)
from planning.gen import planning_pb2

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
        title=Title("Test Story"),
        brief=Brief("Test brief"),
        state=StoryState(StoryStateEnum.DRAFT),
        dor_score=DORScore(0),
        created_by=UserName("po-user"),
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def servicer():
    """Create servicer with mocked use cases (27 total: 18 original + 9 backlog review)."""
    # Project use cases
    create_project_uc = AsyncMock()
    delete_project_uc = AsyncMock()
    get_project_uc = AsyncMock()
    list_projects_uc = AsyncMock()
    # Epic use cases
    create_epic_uc = AsyncMock()
    delete_epic_uc = AsyncMock()
    get_epic_uc = AsyncMock()
    list_epics_uc = AsyncMock()
    # Story use cases
    create_story_uc = AsyncMock()
    delete_story_uc = AsyncMock()
    get_story_uc = AsyncMock()
    list_uc = AsyncMock()
    transition_uc = AsyncMock()
    # Task use cases
    create_task_uc = AsyncMock()
    get_task_uc = AsyncMock()
    list_tasks_uc = AsyncMock()
    # Decision use cases
    approve_uc = AsyncMock()
    reject_uc = AsyncMock()
    # Backlog Review Ceremony use cases (9)
    create_backlog_review_ceremony_uc = AsyncMock()
    get_backlog_review_ceremony_uc = AsyncMock()
    list_backlog_review_ceremonies_uc = AsyncMock()
    add_stories_to_review_uc = AsyncMock()
    remove_story_from_review_uc = AsyncMock()
    start_backlog_review_ceremony_uc = AsyncMock()
    approve_review_plan_uc = AsyncMock()
    reject_review_plan_uc = AsyncMock()
    complete_backlog_review_ceremony_uc = AsyncMock()
    cancel_backlog_review_ceremony_uc = AsyncMock()

    return PlanningServiceServicer(
        # Project
        create_project_uc=create_project_uc,
        delete_project_uc=delete_project_uc,
        get_project_uc=get_project_uc,
        list_projects_uc=list_projects_uc,
        # Epic
        create_epic_uc=create_epic_uc,
        delete_epic_uc=delete_epic_uc,
        get_epic_uc=get_epic_uc,
        list_epics_uc=list_epics_uc,
        # Story
        create_story_uc=create_story_uc,
        delete_story_uc=delete_story_uc,
        get_story_uc=get_story_uc,
        list_stories_uc=list_uc,
        transition_story_uc=transition_uc,
        # Task
        create_task_uc=create_task_uc,
        get_task_uc=get_task_uc,
        list_tasks_uc=list_tasks_uc,
        # Decision
        approve_decision_uc=approve_uc,
        reject_decision_uc=reject_uc,
        # Backlog Review Ceremony
        create_backlog_review_ceremony_uc=create_backlog_review_ceremony_uc,
        get_backlog_review_ceremony_uc=get_backlog_review_ceremony_uc,
        list_backlog_review_ceremonies_uc=list_backlog_review_ceremonies_uc,
        add_stories_to_review_uc=add_stories_to_review_uc,
        remove_story_from_review_uc=remove_story_from_review_uc,
        start_backlog_review_ceremony_uc=start_backlog_review_ceremony_uc,
        approve_review_plan_uc=approve_review_plan_uc,
        reject_review_plan_uc=reject_review_plan_uc,
        complete_backlog_review_ceremony_uc=complete_backlog_review_ceremony_uc,
        cancel_backlog_review_ceremony_uc=cancel_backlog_review_ceremony_uc,
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
    assert call_kwargs["title"].value == "Test Story"
    assert call_kwargs["brief"].value == "Test brief"
    assert call_kwargs["created_by"].value == "po-user"


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
    servicer.get_story_uc.execute.return_value = sample_story

    request = planning_pb2.GetStoryRequest(story_id="story-123")

    response = await servicer.GetStory(request, mock_context)

    assert response.story_id == "story-123"
    assert response.title == "Test Story"

    servicer.get_story_uc.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_story_not_found(servicer, mock_context):
    """Test GetStory when story doesn't exist."""
    servicer.get_story_uc.execute.return_value = None

    request = planning_pb2.GetStoryRequest(story_id="nonexistent")

    response = await servicer.GetStory(request, mock_context)

    # Returns empty Story protobuf
    assert response.story_id == ""
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.NOT_FOUND)


@pytest.mark.asyncio
async def test_get_story_error(servicer, mock_context):
    """Test GetStory with error."""
    servicer.get_story_uc.execute.side_effect = Exception("Database error")

    request = planning_pb2.GetStoryRequest(story_id="story-123")

    response = await servicer.GetStory(request, mock_context)

    assert response.story_id == ""
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)


# Mapper conversion is now tested in test_story_protobuf_mapper.py
# This test is no longer needed as _story_to_pb was moved to StoryProtobufMapper


# ========== Delete Operations Tests ==========


@pytest.mark.asyncio
async def test_delete_project_success(servicer, mock_context):
    """Test DeleteProject with successful deletion."""
    servicer.delete_project_uc.execute = AsyncMock()

    request = planning_pb2.DeleteProjectRequest(project_id="PROJ-123")

    response = await servicer.DeleteProject(request, mock_context)

    assert response.success is True
    assert "deleted" in response.message.lower() or "success" in response.message.lower()

    servicer.delete_project_uc.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_project_validation_error(servicer, mock_context):
    """Test DeleteProject with validation error."""
    servicer.delete_project_uc.execute.side_effect = ValueError("project_id cannot be empty")

    request = planning_pb2.DeleteProjectRequest(project_id="")

    response = await servicer.DeleteProject(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_delete_epic_success(servicer, mock_context):
    """Test DeleteEpic with successful deletion."""
    servicer.delete_epic_uc.execute = AsyncMock()

    request = planning_pb2.DeleteEpicRequest(epic_id="E-456")

    response = await servicer.DeleteEpic(request, mock_context)

    assert response.success is True
    assert "deleted" in response.message.lower() or "success" in response.message.lower()

    servicer.delete_epic_uc.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_epic_validation_error(servicer, mock_context):
    """Test DeleteEpic with validation error."""
    servicer.delete_epic_uc.execute.side_effect = ValueError("epic_id cannot be empty")

    request = planning_pb2.DeleteEpicRequest(epic_id="")

    response = await servicer.DeleteEpic(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_delete_story_success(servicer, mock_context):
    """Test DeleteStory with successful deletion."""
    servicer.delete_story_uc.execute = AsyncMock()

    request = planning_pb2.DeleteStoryRequest(story_id="s-789")

    response = await servicer.DeleteStory(request, mock_context)

    assert response.success is True
    assert "deleted" in response.message.lower() or "success" in response.message.lower()

    servicer.delete_story_uc.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_story_validation_error(servicer, mock_context):
    """Test DeleteStory with validation error."""
    servicer.delete_story_uc.execute.side_effect = ValueError("story_id cannot be empty")

    request = planning_pb2.DeleteStoryRequest(story_id="")

    response = await servicer.DeleteStory(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


# ========== Project Management Tests ==========


@pytest.mark.asyncio
async def test_create_project_success(servicer, mock_context):
    """Test CreateProject with successful creation."""
    from planning.domain.entities.project import Project
    from planning.domain.value_objects.identifiers.project_id import ProjectId
    from planning.domain.value_objects.statuses.project_status import ProjectStatus

    mock_project = Project(
        project_id=ProjectId("PROJ-TEST"),
        name="Test Project",
        description="Test description",
        status=ProjectStatus(ProjectStatus.ACTIVE),
        owner="po-user",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    servicer.create_project_uc.execute.return_value = mock_project

    request = planning_pb2.CreateProjectRequest(
        name="Test Project",
        description="Test description",
        owner="po-user",
    )

    response = await servicer.CreateProject(request, mock_context)

    assert response.success is True
    assert response.project.project_id == "PROJ-TEST"
    assert response.project.name == "Test Project"


@pytest.mark.asyncio
async def test_get_project_success(servicer, mock_context):
    """Test GetProject with successful retrieval."""
    from planning.domain.entities.project import Project
    from planning.domain.value_objects.identifiers.project_id import ProjectId
    from planning.domain.value_objects.statuses.project_status import ProjectStatus

    mock_project = Project(
        project_id=ProjectId("PROJ-TEST"),
        name="Test Project",
        description="Test description",
        status=ProjectStatus(ProjectStatus.ACTIVE),
        owner="po-user",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    servicer.get_project_uc.execute.return_value = mock_project

    request = planning_pb2.GetProjectRequest(project_id="PROJ-TEST")

    response = await servicer.GetProject(request, mock_context)

    assert response.success is True
    assert response.project.project_id == "PROJ-TEST"


@pytest.mark.asyncio
async def test_list_projects_success(servicer, mock_context):
    """Test ListProjects with successful retrieval."""
    from planning.domain.entities.project import Project
    from planning.domain.value_objects.identifiers.project_id import ProjectId
    from planning.domain.value_objects.statuses.project_status import ProjectStatus

    mock_projects = [
        Project(
            project_id=ProjectId("PROJ-1"),
            name="Project 1",
            description="Description 1",
            status=ProjectStatus(ProjectStatus.ACTIVE),
            owner="po-user",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
    ]
    servicer.list_projects_uc.execute.return_value = mock_projects

    request = planning_pb2.ListProjectsRequest()

    response = await servicer.ListProjects(request, mock_context)

    assert response.success is True
    assert response.total_count >= 1


# ========== Epic Management Tests ==========


@pytest.mark.asyncio
async def test_create_epic_success(servicer, mock_context):
    """Test CreateEpic with successful creation."""
    from planning.domain.entities.epic import Epic
    from planning.domain.value_objects.identifiers.epic_id import EpicId
    from planning.domain.value_objects.identifiers.project_id import ProjectId
    from planning.domain.value_objects.statuses.epic_status import EpicStatus

    mock_epic = Epic(
        epic_id=EpicId("E-TEST"),
        project_id=ProjectId("PROJ-TEST"),
        title="Test Epic",
        description="Test description",
        status=EpicStatus(EpicStatus.ACTIVE),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    servicer.create_epic_uc.execute.return_value = mock_epic

    request = planning_pb2.CreateEpicRequest(
        project_id="PROJ-TEST",
        title="Test Epic",
        description="Test description",
    )

    response = await servicer.CreateEpic(request, mock_context)

    assert response.success is True
    assert response.epic.epic_id == "E-TEST"
    assert response.epic.title == "Test Epic"


@pytest.mark.asyncio
async def test_get_epic_success(servicer, mock_context):
    """Test GetEpic with successful retrieval."""
    from planning.domain.entities.epic import Epic
    from planning.domain.value_objects.identifiers.epic_id import EpicId
    from planning.domain.value_objects.identifiers.project_id import ProjectId
    from planning.domain.value_objects.statuses.epic_status import EpicStatus

    mock_epic = Epic(
        epic_id=EpicId("E-TEST"),
        project_id=ProjectId("PROJ-TEST"),
        title="Test Epic",
        description="Test description",
        status=EpicStatus(EpicStatus.ACTIVE),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    servicer.get_epic_uc.execute.return_value = mock_epic

    request = planning_pb2.GetEpicRequest(epic_id="E-TEST")

    response = await servicer.GetEpic(request, mock_context)

    assert response.success is True
    assert response.epic.epic_id == "E-TEST"


@pytest.mark.asyncio
async def test_list_epics_success(servicer, mock_context):
    """Test ListEpics with successful retrieval."""
    from planning.domain.entities.epic import Epic
    from planning.domain.value_objects.identifiers.epic_id import EpicId
    from planning.domain.value_objects.identifiers.project_id import ProjectId
    from planning.domain.value_objects.statuses.epic_status import EpicStatus

    mock_epics = [
        Epic(
            epic_id=EpicId("E-1"),
            project_id=ProjectId("PROJ-TEST"),
            title="Epic 1",
            description="Description 1",
            status=EpicStatus(EpicStatus.ACTIVE),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
    ]
    servicer.list_epics_uc.execute.return_value = mock_epics

    request = planning_pb2.ListEpicsRequest(project_id="PROJ-TEST")

    response = await servicer.ListEpics(request, mock_context)

    assert response.success is True
    assert response.total_count >= 1


# ========== Task Management Tests ==========


@pytest.mark.asyncio
async def test_create_task_success(servicer, mock_context):
    """Test CreateTask with successful creation."""
    from planning.domain.entities.task import Task
    from planning.domain.value_objects.identifiers.task_id import TaskId
    from planning.domain.value_objects.identifiers.story_id import StoryId
    from planning.domain.value_objects.statuses.task_status import TaskStatus
    from planning.domain.value_objects.statuses.task_type import TaskType

    mock_task = Task(
        task_id=TaskId("TASK-1"),
        story_id=StoryId("story-123"),
        title="Test Task",
        description="Test description",
        type=TaskType(TaskType.DEVELOPMENT),
        status=TaskStatus(TaskStatus.TODO),
        assigned_to="dev-agent",
        estimated_hours=8,
        priority=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    servicer.create_task_uc.execute.return_value = mock_task

    request = planning_pb2.CreateTaskRequest(
        story_id="story-123",
        title="Test Task",
        description="Test description",
        type="development",
        assigned_to="dev-agent",
        estimated_hours=8,
        priority=1,
    )

    response = await servicer.CreateTask(request, mock_context)

    assert response.success is True
    assert response.task.task_id == "TASK-1"
    assert response.task.title == "Test Task"


@pytest.mark.asyncio
async def test_get_task_success(servicer, mock_context):
    """Test GetTask with successful retrieval."""
    from planning.domain.entities.task import Task
    from planning.domain.value_objects.identifiers.task_id import TaskId
    from planning.domain.value_objects.identifiers.story_id import StoryId
    from planning.domain.value_objects.statuses.task_status import TaskStatus
    from planning.domain.value_objects.statuses.task_type import TaskType

    mock_task = Task(
        task_id=TaskId("TASK-1"),
        story_id=StoryId("story-123"),
        title="Test Task",
        description="Test description",
        type=TaskType(TaskType.DEVELOPMENT),
        status=TaskStatus(TaskStatus.TODO),
        assigned_to="dev-agent",
        estimated_hours=8,
        priority=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    servicer.get_task_uc.execute.return_value = mock_task

    request = planning_pb2.GetTaskRequest(task_id="TASK-1")

    response = await servicer.GetTask(request, mock_context)

    assert response.success is True
    assert response.task.task_id == "TASK-1"


@pytest.mark.asyncio
async def test_list_tasks_success(servicer, mock_context):
    """Test ListTasks with successful retrieval."""
    from planning.domain.entities.task import Task
    from planning.domain.value_objects.identifiers.task_id import TaskId
    from planning.domain.value_objects.identifiers.story_id import StoryId
    from planning.domain.value_objects.statuses.task_status import TaskStatus
    from planning.domain.value_objects.statuses.task_type import TaskType

    mock_tasks = [
        Task(
            task_id=TaskId("TASK-1"),
            story_id=StoryId("story-123"),
            title="Task 1",
            description="Description 1",
            type=TaskType(TaskType.DEVELOPMENT),
            status=TaskStatus(TaskStatus.TODO),
            assigned_to="dev-agent",
            estimated_hours=8,
            priority=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
    ]
    servicer.list_tasks_uc.execute.return_value = mock_tasks

    request = planning_pb2.ListTasksRequest(story_id="story-123")

    response = await servicer.ListTasks(request, mock_context)

    assert response.success is True
    assert response.total_count >= 1


# ========== Backlog Review Ceremony Tests ==========


def _create_mock_ceremony(
    ceremony_id: str = "ceremony-123",
    story_ids: list[str] | None = None,
    status: BacklogReviewCeremonyStatusEnum = BacklogReviewCeremonyStatusEnum.DRAFT,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> BacklogReviewCeremony:
    """Helper function to create mock BacklogReviewCeremony."""
    if story_ids is None:
        story_ids = ["story-1"]
    now = datetime.now(UTC)

    # Determine started_at and completed_at based on status if not explicitly provided
    if started_at is None:
        if status in (BacklogReviewCeremonyStatusEnum.IN_PROGRESS, BacklogReviewCeremonyStatusEnum.COMPLETED):
            started_at = now
        else:
            started_at = None

    if completed_at is None:
        if status == BacklogReviewCeremonyStatusEnum.COMPLETED:
            completed_at = now
        else:
            completed_at = None

    return BacklogReviewCeremony(
        ceremony_id=BacklogReviewCeremonyId(ceremony_id),
        story_ids=tuple(StoryId(sid) for sid in story_ids),
        status=BacklogReviewCeremonyStatus(status),
        created_by=UserName("po-user"),
        created_at=now,
        updated_at=now,
        started_at=started_at,
        completed_at=completed_at,
    )


@pytest.mark.asyncio
async def test_create_backlog_review_ceremony_success(servicer, mock_context):
    """Test CreateBacklogReviewCeremony with successful creation."""
    mock_ceremony = _create_mock_ceremony(
        story_ids=["story-1", "story-2"],
    )
    servicer.create_backlog_review_ceremony_uc.execute.return_value = mock_ceremony

    request = planning_pb2.CreateBacklogReviewCeremonyRequest(
        created_by="po-user",
        story_ids=["story-1", "story-2"],
    )

    response = await servicer.CreateBacklogReviewCeremony(request, mock_context)

    assert response.success is True
    assert response.ceremony.ceremony_id == "ceremony-123"


@pytest.mark.asyncio
async def test_get_backlog_review_ceremony_success(servicer, mock_context):
    """Test GetBacklogReviewCeremony with successful retrieval."""
    mock_ceremony = _create_mock_ceremony()
    servicer.get_backlog_review_ceremony_uc.execute.return_value = mock_ceremony

    request = planning_pb2.GetBacklogReviewCeremonyRequest(ceremony_id="ceremony-123")

    response = await servicer.GetBacklogReviewCeremony(request, mock_context)

    assert response.success is True
    assert response.ceremony.ceremony_id == "ceremony-123"


@pytest.mark.asyncio
async def test_list_backlog_review_ceremonies_success(servicer, mock_context):
    """Test ListBacklogReviewCeremonies with successful retrieval."""
    mock_ceremonies = [
        _create_mock_ceremony(ceremony_id="ceremony-1"),
    ]
    servicer.list_backlog_review_ceremonies_uc.execute.return_value = mock_ceremonies

    request = planning_pb2.ListBacklogReviewCeremoniesRequest()

    response = await servicer.ListBacklogReviewCeremonies(request, mock_context)

    assert response.success is True
    assert response.total_count >= 1


@pytest.mark.asyncio
async def test_add_stories_to_review_success(servicer, mock_context):
    """Test AddStoriesToReview with successful addition."""
    mock_ceremony = _create_mock_ceremony(
        story_ids=["story-1", "story-2"],
    )
    servicer.add_stories_to_review_uc.execute.return_value = mock_ceremony

    request = planning_pb2.AddStoriesToReviewRequest(
        ceremony_id="ceremony-123",
        story_ids=["story-2"],
    )

    response = await servicer.AddStoriesToReview(request, mock_context)

    assert response.success is True
    assert response.ceremony.ceremony_id == "ceremony-123"


@pytest.mark.asyncio
async def test_remove_story_from_review_success(servicer, mock_context):
    """Test RemoveStoryFromReview with successful removal."""
    mock_ceremony = _create_mock_ceremony()
    servicer.remove_story_from_review_uc.execute.return_value = mock_ceremony

    request = planning_pb2.RemoveStoryFromReviewRequest(
        ceremony_id="ceremony-123",
        story_id="story-2",
    )

    response = await servicer.RemoveStoryFromReview(request, mock_context)

    assert response.success is True
    assert response.ceremony.ceremony_id == "ceremony-123"


@pytest.mark.asyncio
async def test_start_backlog_review_ceremony_success(servicer, mock_context):
    """Test StartBacklogReviewCeremony with successful start."""
    now = datetime.now(UTC)
    mock_ceremony = _create_mock_ceremony(
        status=BacklogReviewCeremonyStatusEnum.IN_PROGRESS,
        started_at=now,
    )
    servicer.start_backlog_review_ceremony_uc.execute.return_value = (mock_ceremony, 3)

    request = planning_pb2.StartBacklogReviewCeremonyRequest(
        ceremony_id="ceremony-123",
        started_by="po-user",
    )

    response = await servicer.StartBacklogReviewCeremony(request, mock_context)

    assert response.success is True
    assert response.ceremony.ceremony_id == "ceremony-123"
    assert response.total_deliberations_submitted == 3


@pytest.mark.asyncio
async def test_approve_review_plan_success(servicer, mock_context):
    """Test ApproveReviewPlan with successful approval."""
    now = datetime.now(UTC)
    mock_ceremony = _create_mock_ceremony(
        status=BacklogReviewCeremonyStatusEnum.IN_PROGRESS,
        started_at=now,
    )
    mock_plan = Plan(
        plan_id=PlanId("plan-456"),
        story_ids=(StoryId("story-1"),),
        title=Title("Test Plan"),
        description=Brief("Test description"),
        acceptance_criteria=("Criterion 1",),
    )
    servicer.approve_review_plan_uc.execute.return_value = (mock_plan, mock_ceremony)

    request = planning_pb2.ApproveReviewPlanRequest(
        ceremony_id="ceremony-123",
        story_id="story-1",
        approved_by="po-user",
        po_notes="Looks good",
    )

    response = await servicer.ApproveReviewPlan(request, mock_context)

    assert response.success is True
    assert response.plan_id == "plan-456"


@pytest.mark.asyncio
async def test_reject_review_plan_success(servicer, mock_context):
    """Test RejectReviewPlan with successful rejection."""
    now = datetime.now(UTC)
    mock_ceremony = _create_mock_ceremony(
        status=BacklogReviewCeremonyStatusEnum.IN_PROGRESS,
        started_at=now,
    )
    servicer.reject_review_plan_uc.execute.return_value = mock_ceremony

    request = planning_pb2.RejectReviewPlanRequest(
        ceremony_id="ceremony-123",
        story_id="story-1",
        rejected_by="po-user",
        rejection_reason="Needs more detail",
    )

    response = await servicer.RejectReviewPlan(request, mock_context)

    assert response.success is True
    assert response.ceremony.ceremony_id == "ceremony-123"


@pytest.mark.asyncio
async def test_complete_backlog_review_ceremony_success(servicer, mock_context):
    """Test CompleteBacklogReviewCeremony with successful completion."""
    now = datetime.now(UTC)
    mock_ceremony = _create_mock_ceremony(
        status=BacklogReviewCeremonyStatusEnum.COMPLETED,
        started_at=now,
        completed_at=now,
    )
    servicer.complete_backlog_review_ceremony_uc.execute.return_value = mock_ceremony

    request = planning_pb2.CompleteBacklogReviewCeremonyRequest(
        ceremony_id="ceremony-123",
        completed_by="po-user",
    )

    response = await servicer.CompleteBacklogReviewCeremony(request, mock_context)

    assert response.success is True
    assert response.ceremony.ceremony_id == "ceremony-123"


@pytest.mark.asyncio
async def test_cancel_backlog_review_ceremony_success(servicer, mock_context):
    """Test CancelBacklogReviewCeremony with successful cancellation."""
    mock_ceremony = _create_mock_ceremony(
        status=BacklogReviewCeremonyStatusEnum.CANCELLED,
    )
    servicer.cancel_backlog_review_ceremony_uc.execute.return_value = mock_ceremony

    request = planning_pb2.CancelBacklogReviewCeremonyRequest(
        ceremony_id="ceremony-123",
        cancelled_by="po-user",
    )

    response = await servicer.CancelBacklogReviewCeremony(request, mock_context)

    assert response.success is True
    assert response.ceremony.ceremony_id == "ceremony-123"


@pytest.mark.asyncio
async def test_add_agent_deliberation_success(servicer, mock_context):
    """Test AddAgentDeliberation with successful addition."""
    now = datetime.now(UTC)
    mock_ceremony = _create_mock_ceremony(
        status=BacklogReviewCeremonyStatusEnum.IN_PROGRESS,
        started_at=now,
    )
    servicer.process_story_review_result_uc = AsyncMock()
    servicer.process_story_review_result_uc.execute.return_value = mock_ceremony

    request = planning_pb2.AddAgentDeliberationRequest(
        ceremony_id="ceremony-123",
        story_id="story-1",
        role="ARCHITECT",
        agent_id="agent-1",
        feedback="Good approach",
        proposal='{"tasks": ["task1"]}',
        reviewed_at=datetime.now(UTC).isoformat(),
    )

    response = await servicer.AddAgentDeliberation(request, mock_context)

    assert response.success is True
    assert response.ceremony.ceremony_id == "ceremony-123"


# ========== Error Handling Tests ==========


@pytest.mark.asyncio
async def test_create_project_validation_error(servicer, mock_context):
    """Test CreateProject with validation error."""
    servicer.create_project_uc.execute.side_effect = ValueError("Name cannot be empty")

    request = planning_pb2.CreateProjectRequest(name="", owner="po-user")

    response = await servicer.CreateProject(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_get_project_not_found(servicer, mock_context):
    """Test GetProject when project doesn't exist."""
    servicer.get_project_uc.execute.return_value = None

    request = planning_pb2.GetProjectRequest(project_id="PROJ-NOT-FOUND")

    response = await servicer.GetProject(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.NOT_FOUND)


@pytest.mark.asyncio
async def test_create_epic_validation_error(servicer, mock_context):
    """Test CreateEpic with validation error."""
    servicer.create_epic_uc.execute.side_effect = ValueError("Title cannot be empty")

    request = planning_pb2.CreateEpicRequest(
        project_id="PROJ-123",
        title="",
        description="Test",
    )

    response = await servicer.CreateEpic(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_get_epic_not_found(servicer, mock_context):
    """Test GetEpic when epic doesn't exist."""
    servicer.get_epic_uc.execute.return_value = None

    request = planning_pb2.GetEpicRequest(epic_id="E-NOT-FOUND")

    response = await servicer.GetEpic(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.NOT_FOUND)


@pytest.mark.asyncio
async def test_create_task_validation_error(servicer, mock_context):
    """Test CreateTask with validation error."""
    servicer.create_task_uc.execute.side_effect = ValueError("Title cannot be empty")

    request = planning_pb2.CreateTaskRequest(
        story_id="story-123",
        title="",
        description="Test",
        type="development",
        assigned_to="dev",
        estimated_hours=8,
        priority=1,
    )

    response = await servicer.CreateTask(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_get_task_not_found(servicer, mock_context):
    """Test GetTask when task doesn't exist."""
    servicer.get_task_uc.execute.return_value = None

    request = planning_pb2.GetTaskRequest(task_id="TASK-NOT-FOUND")

    response = await servicer.GetTask(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.NOT_FOUND)


@pytest.mark.asyncio
async def test_delete_project_internal_error(servicer, mock_context):
    """Test DeleteProject with internal error."""
    servicer.delete_project_uc.execute.side_effect = Exception("Database error")

    request = planning_pb2.DeleteProjectRequest(project_id="PROJ-123")

    response = await servicer.DeleteProject(request, mock_context)

    assert response.success is False
    assert "Internal error" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)


@pytest.mark.asyncio
async def test_delete_epic_internal_error(servicer, mock_context):
    """Test DeleteEpic with internal error."""
    servicer.delete_epic_uc.execute.side_effect = Exception("Database error")

    request = planning_pb2.DeleteEpicRequest(epic_id="E-456")

    response = await servicer.DeleteEpic(request, mock_context)

    assert response.success is False
    assert "Internal error" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)


@pytest.mark.asyncio
async def test_delete_story_internal_error(servicer, mock_context):
    """Test DeleteStory with internal error."""
    servicer.delete_story_uc.execute.side_effect = Exception("Database error")

    request = planning_pb2.DeleteStoryRequest(story_id="s-789")

    response = await servicer.DeleteStory(request, mock_context)

    assert response.success is False
    assert "Internal error" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)


@pytest.mark.asyncio
async def test_create_backlog_review_ceremony_validation_error(servicer, mock_context):
    """Test CreateBacklogReviewCeremony with validation error."""
    servicer.create_backlog_review_ceremony_uc.execute.side_effect = ValueError(
        "created_by cannot be empty"
    )

    request = planning_pb2.CreateBacklogReviewCeremonyRequest(created_by="")

    response = await servicer.CreateBacklogReviewCeremony(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_get_backlog_review_ceremony_not_found(servicer, mock_context):
    """Test GetBacklogReviewCeremony when ceremony doesn't exist."""
    servicer.get_backlog_review_ceremony_uc.execute.return_value = None

    request = planning_pb2.GetBacklogReviewCeremonyRequest(ceremony_id="ceremony-not-found")

    response = await servicer.GetBacklogReviewCeremony(request, mock_context)

    assert response.success is False
    assert "not found" in response.message.lower()


@pytest.mark.asyncio
async def test_add_stories_to_review_validation_error(servicer, mock_context):
    """Test AddStoriesToReview with validation error."""
    servicer.add_stories_to_review_uc.execute.side_effect = ValueError("Ceremony not found")

    request = planning_pb2.AddStoriesToReviewRequest(
        ceremony_id="ceremony-123",
        story_ids=["story-1"],
    )

    response = await servicer.AddStoriesToReview(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_remove_story_from_review_validation_error(servicer, mock_context):
    """Test RemoveStoryFromReview with validation error."""
    servicer.remove_story_from_review_uc.execute.side_effect = ValueError("Story not in ceremony")

    request = planning_pb2.RemoveStoryFromReviewRequest(
        ceremony_id="ceremony-123",
        story_id="story-999",
    )

    response = await servicer.RemoveStoryFromReview(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_start_backlog_review_ceremony_validation_error(servicer, mock_context):
    """Test StartBacklogReviewCeremony with validation error."""
    servicer.start_backlog_review_ceremony_uc.execute.side_effect = ValueError(
        "Ceremony not found"
    )

    request = planning_pb2.StartBacklogReviewCeremonyRequest(
        ceremony_id="ceremony-123",
        started_by="po-user",
    )

    response = await servicer.StartBacklogReviewCeremony(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_approve_review_plan_validation_error(servicer, mock_context):
    """Test ApproveReviewPlan with validation error."""
    servicer.approve_review_plan_uc.execute.side_effect = ValueError("po_notes is required")

    request = planning_pb2.ApproveReviewPlanRequest(
        ceremony_id="ceremony-123",
        story_id="story-1",
        approved_by="po-user",
        po_notes="",  # Empty notes should fail
    )

    response = await servicer.ApproveReviewPlan(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_reject_review_plan_validation_error(servicer, mock_context):
    """Test RejectReviewPlan with validation error."""
    servicer.reject_review_plan_uc.execute.side_effect = ValueError("rejection_reason is required")

    request = planning_pb2.RejectReviewPlanRequest(
        ceremony_id="ceremony-123",
        story_id="story-1",
        rejected_by="po-user",
        rejection_reason="",  # Empty reason should fail
    )

    response = await servicer.RejectReviewPlan(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_complete_backlog_review_ceremony_validation_error(servicer, mock_context):
    """Test CompleteBacklogReviewCeremony with validation error."""
    servicer.complete_backlog_review_ceremony_uc.execute.side_effect = ValueError(
        "Ceremony not found"
    )

    request = planning_pb2.CompleteBacklogReviewCeremonyRequest(
        ceremony_id="ceremony-123",
        completed_by="po-user",
    )

    response = await servicer.CompleteBacklogReviewCeremony(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_cancel_backlog_review_ceremony_validation_error(servicer, mock_context):
    """Test CancelBacklogReviewCeremony with validation error."""
    servicer.cancel_backlog_review_ceremony_uc.execute.side_effect = ValueError(
        "Ceremony not found"
    )

    request = planning_pb2.CancelBacklogReviewCeremonyRequest(
        ceremony_id="ceremony-123",
        cancelled_by="po-user",
    )

    response = await servicer.CancelBacklogReviewCeremony(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_add_agent_deliberation_validation_error(servicer, mock_context):
    """Test AddAgentDeliberation with validation error."""
    servicer.process_story_review_result_uc = AsyncMock()
    servicer.process_story_review_result_uc.execute.side_effect = ValueError(
        "Ceremony not found"
    )

    request = planning_pb2.AddAgentDeliberationRequest(
        ceremony_id="ceremony-123",
        story_id="story-1",
        role="ARCHITECT",
        agent_id="agent-1",
        feedback="Feedback",
        proposal='{"tasks": []}',
        reviewed_at=datetime.now(UTC).isoformat(),
    )

    response = await servicer.AddAgentDeliberation(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


# ========== Servicer Initialization Test ==========


def test_servicer_initialization(servicer):
    """Test that servicer can be instantiated with all required use cases."""
    assert servicer is not None
    # Verify all delete use cases are present
    assert servicer.delete_project_uc is not None
    assert servicer.delete_epic_uc is not None
    assert servicer.delete_story_uc is not None
    # Verify other critical use cases
    assert servicer.create_project_uc is not None
    assert servicer.get_project_uc is not None
    assert servicer.list_projects_uc is not None
    assert servicer.create_epic_uc is not None
    assert servicer.get_epic_uc is not None
    assert servicer.list_epics_uc is not None
    assert servicer.create_story_uc is not None
    assert servicer.get_story_uc is not None
    assert servicer.list_stories_uc is not None
    assert servicer.transition_story_uc is not None
    assert servicer.create_task_uc is not None
    assert servicer.get_task_uc is not None
    assert servicer.list_tasks_uc is not None
    assert servicer.approve_decision_uc is not None
    assert servicer.reject_decision_uc is not None
    # Verify backlog review ceremony use cases
    assert servicer.create_backlog_review_ceremony_uc is not None
    assert servicer.get_backlog_review_ceremony_uc is not None
    assert servicer.list_backlog_review_ceremonies_uc is not None
    assert servicer.add_stories_to_review_uc is not None
    assert servicer.remove_story_from_review_uc is not None
    assert servicer.start_backlog_review_ceremony_uc is not None
    assert servicer.approve_review_plan_uc is not None
    assert servicer.reject_review_plan_uc is not None
    assert servicer.complete_backlog_review_ceremony_uc is not None
    assert servicer.cancel_backlog_review_ceremony_uc is not None


# ========== StartPlanningCeremony (optional processor) ==========


@pytest.mark.asyncio
async def test_start_planning_ceremony_not_configured(servicer, mock_context):
    """Test StartPlanningCeremony when planning_ceremony_processor_uc is None."""
    servicer.planning_ceremony_processor_uc = None

    request = planning_pb2.StartPlanningCeremonyRequest(
        ceremony_id="ceremony-1",
        definition_name="e2e_multi_step",
        story_id="s-1",
        correlation_id="c1",
        step_ids=["deliberate"],
        requested_by="user@test",
        inputs={},
    )

    response = await servicer.StartPlanningCeremony(request, mock_context)

    assert response.instance_id == ""
    assert "not configured" in response.message.lower() or "processor" in response.message.lower()
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.FAILED_PRECONDITION)


@pytest.mark.asyncio
async def test_start_planning_ceremony_configured_success(servicer, mock_context):
    """Test StartPlanningCeremony when processor use case is set."""
    servicer.planning_ceremony_processor_uc = AsyncMock()
    servicer.planning_ceremony_processor_uc.execute = AsyncMock(
        return_value="inst-ceremony-1"
    )

    request = planning_pb2.StartPlanningCeremonyRequest(
        ceremony_id="ceremony-1",
        definition_name="e2e_multi_step",
        story_id="s-1",
        correlation_id="c1",
        step_ids=["deliberate"],
        requested_by="user@test",
        inputs={},
    )

    response = await servicer.StartPlanningCeremony(request, mock_context)

    assert response.instance_id == "inst-ceremony-1"
    servicer.planning_ceremony_processor_uc.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_planning_ceremony_not_configured(servicer, mock_context):
    """Test GetPlanningCeremony when processor use case is not configured."""
    servicer.get_planning_ceremony_processor_uc = None

    request = planning_pb2.GetPlanningCeremonyRequest(instance_id="inst-1")
    response = await servicer.GetPlanningCeremony(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.FAILED_PRECONDITION)


@pytest.mark.asyncio
async def test_get_planning_ceremony_configured_success(servicer, mock_context):
    """Test GetPlanningCeremony happy path via handler."""
    servicer.get_planning_ceremony_processor_uc = AsyncMock()
    servicer.get_planning_ceremony_processor_uc.execute = AsyncMock(
        return_value=type(
            "PlanningCeremonyData",
            (),
            {
                "instance_id": "inst-1",
                "ceremony_id": "cer-1",
                "story_id": "story-1",
                "definition_name": "dummy_ceremony",
                "current_state": "in_progress",
                "status": "IN_PROGRESS",
                "correlation_id": "corr-1",
                "step_status": {},
                "step_outputs": {},
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:01:00+00:00",
            },
        )()
    )

    request = planning_pb2.GetPlanningCeremonyRequest(instance_id="inst-1")
    response = await servicer.GetPlanningCeremony(request, mock_context)

    assert response.success is True
    assert response.ceremony.instance_id == "inst-1"


@pytest.mark.asyncio
async def test_list_planning_ceremonies_not_configured(servicer, mock_context):
    """Test ListPlanningCeremonies when processor use case is not configured."""
    servicer.list_planning_ceremonies_processor_uc = None

    request = planning_pb2.ListPlanningCeremoniesRequest(limit=10, offset=0)
    response = await servicer.ListPlanningCeremonies(request, mock_context)

    assert response.success is False
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.FAILED_PRECONDITION)


@pytest.mark.asyncio
async def test_list_planning_ceremonies_configured_success(servicer, mock_context):
    """Test ListPlanningCeremonies happy path via handler."""
    servicer.list_planning_ceremonies_processor_uc = AsyncMock()
    servicer.list_planning_ceremonies_processor_uc.execute = AsyncMock(
        return_value=([], 0)
    )

    request = planning_pb2.ListPlanningCeremoniesRequest(limit=10, offset=0)
    response = await servicer.ListPlanningCeremonies(request, mock_context)

    assert response.success is True
    assert response.total_count == 0


# ========== Main Function Tests ==========


@pytest.mark.asyncio
async def test_main_initialization_with_mocks():
    """Test main() function initialization with mocked dependencies."""
    from unittest.mock import AsyncMock, MagicMock, patch

    # Mock all external dependencies
    mock_config = MagicMock()
    mock_config.get_grpc_port.return_value = 50054
    mock_config.get_nats_url.return_value = "nats://localhost:4222"
    mock_config.get_neo4j_uri.return_value = "bolt://localhost:7687"
    mock_config.get_neo4j_user.return_value = "neo4j"
    mock_config.get_neo4j_password.return_value = "password"
    mock_config.get_neo4j_database.return_value = "neo4j"
    mock_config.get_valkey_host.return_value = "localhost"
    mock_config.get_valkey_port.return_value = 6379
    mock_config.get_valkey_db.return_value = 0
    mock_config.get_ray_executor_url.return_value = "localhost:50051"
    mock_config.get_vllm_url.return_value = "http://localhost:8000"
    mock_config.get_vllm_model.return_value = "model"
    mock_config.get_context_service_url.return_value = "localhost:50052"
    # Optional: not used by backlog review (decoupled from ceremony processor)
    mock_config.get_planning_ceremony_processor_url.return_value = None

    mock_nats = AsyncMock()
    mock_jetstream = AsyncMock()
    mock_nats.connect = AsyncMock()
    mock_nats.jetstream.return_value = mock_jetstream
    mock_nats.close = AsyncMock()

    mock_storage = MagicMock()
    mock_storage.close = MagicMock()

    mock_consumer = AsyncMock()
    mock_consumer.start = AsyncMock()
    mock_consumer.stop = AsyncMock()

    mock_grpc_server = AsyncMock()
    mock_grpc_server.start = AsyncMock()
    mock_grpc_server.wait_for_termination = AsyncMock(side_effect=KeyboardInterrupt())
    mock_grpc_server.stop = AsyncMock()
    mock_grpc_server.add_insecure_port = MagicMock()

    mock_dual_write_ledger = MagicMock()
    mock_reconciliation_service = AsyncMock()

    with patch("server.EnvironmentConfigurationAdapter", return_value=mock_config), \
         patch("server.NATS", return_value=mock_nats), \
         patch("server.StorageAdapter", return_value=mock_storage), \
         patch("server.ValkeyDualWriteLedgerAdapter", return_value=mock_dual_write_ledger), \
         patch("server.DualWriteReconciliationService", return_value=mock_reconciliation_service), \
         patch("server.DualWriteReconcilerConsumer", return_value=mock_consumer), \
         patch("server.NATSMessagingAdapter"), \
         patch("server.RayExecutorAdapter"), \
         patch("server.ContextServiceAdapter"), \
         patch("server.TaskDerivationResultService"), \
         patch("server.TaskDerivationResultConsumer", return_value=mock_consumer), \
         patch("server.DeliberationsCompleteProgressConsumer", return_value=mock_consumer), \
         patch("server.TasksCompleteProgressConsumer", return_value=mock_consumer), \
         patch("server.grpc.aio.server", return_value=mock_grpc_server), \
         patch("server.planning_pb2_grpc.add_PlanningServiceServicer_to_server"):

        from server import main

        # Run main() but it will be interrupted by KeyboardInterrupt
        try:
            await main()
        except KeyboardInterrupt:
            pass  # Expected

        # Verify key initializations happened
        mock_config.get_grpc_port.assert_called_once()
        mock_nats.connect.assert_awaited_once()
        mock_consumer.start.assert_awaited()
        mock_grpc_server.start.assert_awaited_once()
        mock_grpc_server.wait_for_termination.assert_awaited_once()
        mock_consumer.stop.assert_awaited()
        mock_grpc_server.stop.assert_awaited_once()
        mock_storage.close.assert_called_once()
        mock_nats.close.assert_awaited_once()
