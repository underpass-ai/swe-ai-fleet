"""Unit tests for PlanningEventMapper (payload_to_*, from_redis_data)."""

import pytest

from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.plan_id import PlanId
from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.epic import Epic
from core.context.domain.plan_approval import PlanApproval
from core.context.domain.phase_transition import PhaseTransition
from core.context.domain.project import Project
from core.context.domain.story import Story
from core.context.domain.task import Task
from core.context.infrastructure.mappers.planning_event_mapper import PlanningEventMapper


class TestFromRedisData:
    """Tests for from_redis_data (Redis/Valkey event → PlanningEvent)."""

    def test_from_redis_data_minimal(self) -> None:
        """Build PlanningEvent from minimal Redis dict."""
        data = {
            "id": "ev-1",
            "event": "story.created",
            "actor": "user@test",
            "payload": {},
        }
        event = PlanningEventMapper.from_redis_data(data)
        assert event.id == "ev-1"
        assert event.event == "story.created"
        assert event.actor_id.value == "user@test"
        assert event.payload == {}
        assert event.ts_ms == 0

    def test_from_redis_data_with_ts_ms_and_payload(self) -> None:
        """Build PlanningEvent with ts_ms and payload."""
        data = {
            "id": "ev-2",
            "event": "plan.approved",
            "actor": "po@test",
            "payload": {"plan_id": "P-1", "story_id": "s-1"},
            "ts_ms": 1234567890,
        }
        event = PlanningEventMapper.from_redis_data(data)
        assert event.ts_ms == 1234567890
        assert event.payload == {"plan_id": "P-1", "story_id": "s-1"}


class TestPayloadToProject:
    """Tests for payload_to_project."""

    def test_payload_to_project_minimal(self) -> None:
        """Project from minimal payload (defaults for optional)."""
        payload = {"project_id": "PROJ-1", "name": "My Project"}
        project = PlanningEventMapper.payload_to_project(payload)
        assert project.project_id == ProjectId("PROJ-1")
        assert project.name == "My Project"
        assert project.description == ""
        assert project.status.value == "active"
        assert project.owner == ""
        assert project.created_at_ms == 0

    def test_payload_to_project_full(self) -> None:
        """Project with all fields."""
        payload = {
            "project_id": "PROJ-2",
            "name": "Full",
            "description": "Desc",
            "status": "archived",
            "owner": "owner@test",
            "created_at_ms": 999,
        }
        project = PlanningEventMapper.payload_to_project(payload)
        assert project.description == "Desc"
        assert project.status.value == "archived"
        assert project.owner == "owner@test"
        assert project.created_at_ms == 999


class TestPayloadToEpic:
    """Tests for payload_to_epic."""

    def test_payload_to_epic_minimal(self) -> None:
        """Epic from minimal payload."""
        payload = {"epic_id": "E-1", "project_id": "PROJ-1", "title": "Epic Title"}
        epic = PlanningEventMapper.payload_to_epic(payload)
        assert epic.epic_id == EpicId("E-1")
        assert epic.project_id == ProjectId("PROJ-1")
        assert epic.title == "Epic Title"
        assert epic.description == ""
        assert epic.status.value == "active"
        assert epic.created_at_ms == 0

    def test_payload_to_epic_full(self) -> None:
        """Epic with optional fields."""
        payload = {
            "epic_id": "E-2",
            "project_id": "PROJ-2",
            "title": "Epic 2",
            "description": "D",
            "status": "completed",
            "created_at_ms": 100,
        }
        epic = PlanningEventMapper.payload_to_epic(payload)
        assert epic.description == "D"
        assert epic.status.value == "completed"
        assert epic.created_at_ms == 100


class TestPayloadToStory:
    """Test suite for payload_to_story (planning.story.created → Story)."""

    def test_payload_to_story_happy_path_with_name(self) -> None:
        """Story built when payload has story_id, epic_id, name."""
        payload = {
            "story_id": "s-123",
            "epic_id": "E-456",
            "name": "As a user I want to login",
        }
        story = PlanningEventMapper.payload_to_story(payload)
        assert isinstance(story, Story)
        assert story.story_id == StoryId("s-123")
        assert story.epic_id == EpicId("E-456")
        assert story.name == "As a user I want to login"

    def test_payload_to_story_happy_path_with_title(self) -> None:
        """Story built when payload has title (Planning BC) instead of name."""
        payload = {
            "story_id": "s-789",
            "epic_id": "E-ABC",
            "title": "As a user I want to logout",
        }
        story = PlanningEventMapper.payload_to_story(payload)
        assert story.story_id == StoryId("s-789")
        assert story.epic_id == EpicId("E-ABC")
        assert story.name == "As a user I want to logout"

    def test_payload_to_story_missing_story_id_raises(self) -> None:
        """Missing story_id raises ValueError (fail-fast)."""
        payload = {"epic_id": "E-1", "name": "A story"}
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_story(payload)
        assert "story_id" in str(exc_info.value)
        assert "story.created" in str(exc_info.value).lower()

    def test_payload_to_story_missing_epic_id_raises(self) -> None:
        """Missing epic_id raises ValueError (fail-fast, no KeyError)."""
        payload = {"story_id": "s-1", "name": "A story"}
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_story(payload)
        assert "epic_id" in str(exc_info.value)
        assert "Epic" in str(exc_info.value) or "epic" in str(exc_info.value).lower()

    def test_payload_to_story_missing_name_and_title_raises(self) -> None:
        """Missing both name and title raises ValueError."""
        payload = {"story_id": "s-1", "epic_id": "E-1"}
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_story(payload)
        assert "name" in str(exc_info.value) or "title" in str(exc_info.value)

    def test_payload_to_story_empty_name_raises(self) -> None:
        """Empty name (whitespace only) raises ValueError."""
        payload = {"story_id": "s-1", "epic_id": "E-1", "name": "   "}
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_story(payload)
        assert "name" in str(exc_info.value) or "title" in str(exc_info.value)

    def test_payload_to_story_name_or_title_must_be_str(self) -> None:
        """name/title must be str; non-str raises ValueError (no conversion)."""
        payload = {"story_id": "s-1", "epic_id": "E-1", "title": 123}
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_story(payload)
        assert "must be str" in str(exc_info.value)
        assert "int" in str(exc_info.value)

    def test_payload_to_story_story_id_must_be_str(self) -> None:
        """story_id must be str; non-str raises ValueError."""
        payload = {"story_id": 123, "epic_id": "E-1", "name": "A story"}
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_story(payload)
        assert "story_id" in str(exc_info.value)
        assert "str" in str(exc_info.value)

    def test_payload_to_story_epic_id_must_be_str(self) -> None:
        """epic_id must be str; non-str raises ValueError."""
        payload = {"story_id": "s-1", "epic_id": None, "name": "A story"}
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_story(payload)
        assert "epic_id" in str(exc_info.value)
        assert "str" in str(exc_info.value)


class TestPayloadToTask:
    """Tests for payload_to_task."""

    def test_payload_to_task_minimal(self) -> None:
        """Task from minimal payload."""
        payload = {"task_id": "T-1", "plan_id": "P-1", "title": "Task Title"}
        task = PlanningEventMapper.payload_to_task(payload)
        assert task.task_id == TaskId("T-1")
        assert task.plan_id == PlanId("P-1")
        assert task.title == "Task Title"
        assert task.type.value == "development"
        assert task.status.value == "todo"

    def test_payload_to_task_full(self) -> None:
        """Task with type and status."""
        payload = {
            "task_id": "T-2",
            "plan_id": "P-2",
            "title": "Task 2",
            "type": "testing",
            "status": "done",
        }
        task = PlanningEventMapper.payload_to_task(payload)
        assert task.type.value == "testing"
        assert task.status.value == "done"


class TestPayloadToPlanApproval:
    """Tests for payload_to_plan_approval."""

    def test_payload_to_plan_approval_with_approved_at(self) -> None:
        """PlanApproval from payload with approved_at (Planning BC)."""
        payload = {
            "plan_id": "P-1",
            "story_id": "s-1",
            "approved_by": "po@test",
            "approved_at": "2025-01-01T12:00:00Z",
        }
        approval = PlanningEventMapper.payload_to_plan_approval(payload)
        assert approval.plan_id == PlanId("P-1")
        assert approval.story_id == StoryId("s-1")
        assert approval.approved_by == "po@test"
        assert approval.timestamp == "2025-01-01T12:00:00Z"

    def test_payload_to_plan_approval_with_timestamp(self) -> None:
        """PlanApproval from payload with timestamp (Context BC)."""
        payload = {
            "plan_id": "P-2",
            "story_id": "s-2",
            "approved_by": "user@test",
            "timestamp": "2025-06-01T00:00:00Z",
        }
        approval = PlanningEventMapper.payload_to_plan_approval(payload)
        assert approval.timestamp == "2025-06-01T00:00:00Z"

    def test_payload_to_plan_approval_missing_plan_id_raises(self) -> None:
        """Missing plan_id raises ValueError."""
        payload = {"story_id": "s-1", "approved_by": "u", "timestamp": "t"}
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_plan_approval(payload)
        assert "plan_id" in str(exc_info.value)

    def test_payload_to_plan_approval_missing_story_id_raises(self) -> None:
        """Missing story_id raises ValueError."""
        payload = {"plan_id": "P-1", "approved_by": "u", "timestamp": "t"}
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_plan_approval(payload)
        assert "story_id" in str(exc_info.value)

    def test_payload_to_plan_approval_missing_timestamp_and_approved_at_raises(
        self,
    ) -> None:
        """Missing both timestamp and approved_at raises ValueError."""
        payload = {"plan_id": "P-1", "story_id": "s-1", "approved_by": "u"}
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_plan_approval(payload)
        assert "timestamp" in str(exc_info.value) or "approved_at" in str(exc_info.value)

    def test_payload_to_plan_approval_plan_id_not_str_raises(self) -> None:
        """plan_id must be str."""
        payload = {
            "plan_id": 123,
            "story_id": "s-1",
            "approved_by": "u",
            "timestamp": "t",
        }
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_plan_approval(payload)
        assert "plan_id" in str(exc_info.value)
        assert "str" in str(exc_info.value)

    def test_payload_to_plan_approval_story_id_not_str_raises(self) -> None:
        """story_id must be str."""
        payload = {
            "plan_id": "P-1",
            "story_id": [],
            "approved_by": "u",
            "timestamp": "t",
        }
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_plan_approval(payload)
        assert "story_id" in str(exc_info.value)

    def test_payload_to_plan_approval_approved_by_not_str_raises(self) -> None:
        """approved_by must be str."""
        payload = {
            "plan_id": "P-1",
            "story_id": "s-1",
            "approved_by": 1,
            "timestamp": "t",
        }
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_plan_approval(payload)
        assert "approved_by" in str(exc_info.value)

    def test_payload_to_plan_approval_timestamp_not_str_raises(self) -> None:
        """timestamp/approved_at must be str."""
        payload = {
            "plan_id": "P-1",
            "story_id": "s-1",
            "approved_by": "u",
            "timestamp": 123,
        }
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_plan_approval(payload)
        assert "timestamp" in str(exc_info.value) or "approved_at" in str(exc_info.value)

    def test_payload_to_plan_approval_empty_timestamp_raises(self) -> None:
        """Empty timestamp (whitespace) raises ValueError."""
        payload = {
            "plan_id": "P-1",
            "story_id": "s-1",
            "approved_by": "u",
            "timestamp": "   ",
        }
        with pytest.raises(ValueError) as exc_info:
            PlanningEventMapper.payload_to_plan_approval(payload)
        assert "empty" in str(exc_info.value).lower()


class TestPayloadToPhaseTransition:
    """Tests for payload_to_phase_transition."""

    def test_payload_to_phase_transition(self) -> None:
        """PhaseTransition from planning.story.transitioned payload."""
        payload = {
            "story_id": "s-1",
            "from_phase": "backlog",
            "to_phase": "in_progress",
            "timestamp": "2025-01-01T00:00:00Z",
        }
        transition = PlanningEventMapper.payload_to_phase_transition(payload)
        assert transition.story_id == StoryId("s-1")
        assert transition.from_phase == "backlog"
        assert transition.to_phase == "in_progress"
        assert transition.timestamp == "2025-01-01T00:00:00Z"
