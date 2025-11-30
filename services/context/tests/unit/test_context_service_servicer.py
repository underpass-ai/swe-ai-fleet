"""
Unit tests for ContextServiceServicer gRPC methods.

Tests all gRPC handlers with mocked dependencies following Hexagonal Architecture.
Target: ≥90% coverage with comprehensive edge case testing.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import grpc
import pytest
from grpc.aio import ServicerContext

from services.context.gen import context_pb2
from services.context.server import ContextServiceServicer

pytestmark = pytest.mark.unit


# Test fixtures
@pytest.fixture
def mock_grpc_context() -> MagicMock:
    """Create mock gRPC context."""
    context = MagicMock(spec=ServicerContext)
    context.set_code = MagicMock()
    context.set_details = MagicMock()
    return context


@pytest.fixture
def mock_neo4j_query_store() -> MagicMock:
    """Create mock Neo4j query store."""
    return MagicMock()


@pytest.fixture
def mock_neo4j_command_store() -> MagicMock:
    """Create mock Neo4j command store."""
    store = MagicMock()
    store.upsert_entity = MagicMock()
    store.relate = MagicMock()
    store.execute_write = MagicMock()
    return store


@pytest.fixture
def mock_redis_client() -> MagicMock:
    """Create mock Redis client."""
    client = MagicMock()
    client.hset = MagicMock()
    return client


@pytest.fixture
def mock_planning_read_adapter(mock_redis_client: MagicMock) -> MagicMock:
    """Create mock Redis planning read adapter."""
    adapter = MagicMock()
    adapter.client = mock_redis_client
    return adapter


@pytest.fixture
def mock_rehydrator() -> MagicMock:
    """Create mock SessionRehydrationApplicationService."""
    rehydrator = MagicMock()
    rehydrator.build = MagicMock()
    return rehydrator


@pytest.fixture
def mock_policy() -> MagicMock:
    """Create mock PromptScopePolicy."""
    policy = MagicMock()
    scope_check = MagicMock()
    scope_check.allowed = True
    scope_check.missing = set()
    scope_check.extra = set()
    policy.check = MagicMock(return_value=scope_check)
    return policy


@pytest.fixture
def mock_use_cases() -> dict[str, MagicMock]:
    """Create mock use cases."""
    return {
        "project_story_uc": MagicMock(),
        "project_task_uc": MagicMock(),
        "project_plan_version_uc": MagicMock(),
        "project_decision_uc": MagicMock(),
        "record_milestone_uc": MagicMock(),
        "get_graph_relationships_uc": MagicMock(),
        "process_context_change_uc": MagicMock(),
    }


@pytest.fixture
def mock_nats_handler() -> MagicMock:
    """Create mock NATS handler."""
    handler = MagicMock()
    handler.publish_context_updated = AsyncMock()
    return handler


@pytest.fixture
def servicer(
    mock_neo4j_query_store: MagicMock,
    mock_neo4j_command_store: MagicMock,
    mock_planning_read_adapter: MagicMock,
    mock_rehydrator: MagicMock,
    mock_policy: MagicMock,
    mock_use_cases: dict[str, MagicMock],
    mock_nats_handler: MagicMock | None,
) -> ContextServiceServicer:
    """Create ContextServiceServicer with mocked dependencies."""
    with patch("services.context.server.Neo4jQueryStore", return_value=mock_neo4j_query_store), \
         patch("services.context.server.Neo4jCommandStore", return_value=mock_neo4j_command_store), \
         patch("services.context.server.RedisPlanningReadAdapter", return_value=mock_planning_read_adapter), \
         patch("services.context.server.SessionRehydrationApplicationService", return_value=mock_rehydrator), \
         patch("services.context.server.PromptScopePolicy", return_value=mock_policy), \
         patch("services.context.server.ProjectStoryUseCase", return_value=mock_use_cases["project_story_uc"]), \
         patch("services.context.server.ProjectTaskUseCase", return_value=mock_use_cases["project_task_uc"]), \
         patch("services.context.server.ProjectPlanVersionUseCase", return_value=mock_use_cases["project_plan_version_uc"]), \
         patch("services.context.server.ProjectDecisionUseCase", return_value=mock_use_cases["project_decision_uc"]), \
         patch("services.context.server.RecordMilestoneUseCase", return_value=mock_use_cases["record_milestone_uc"]), \
         patch("services.context.server.GetGraphRelationshipsUseCase", return_value=mock_use_cases["get_graph_relationships_uc"]), \
         patch("services.context.server.ProcessContextChangeUseCase", return_value=mock_use_cases["process_context_change_uc"]), \
         patch("services.context.server.Neo4jDecisionGraphReadAdapter", return_value=MagicMock()), \
         patch("services.context.server.RedisStoreImpl"), \
         patch("services.context.server.load_scopes_config", return_value={}):
        servicer = ContextServiceServicer(
            neo4j_uri="bolt://test:7687",
            neo4j_user="test",
            neo4j_password="test",
            redis_host="test",
            redis_port=6379,
            nats_handler=mock_nats_handler,
        )
        # Inject mocked dependencies directly
        servicer.neo4j_query_store = mock_neo4j_query_store
        servicer.graph_query = MagicMock()
        servicer.graph_command = mock_neo4j_command_store
        servicer.planning_read = mock_planning_read_adapter
        servicer.rehydrator = mock_rehydrator
        servicer.policy = mock_policy
        servicer.project_story_uc = mock_use_cases["project_story_uc"]
        servicer.project_task_uc = mock_use_cases["project_task_uc"]
        servicer.project_plan_version_uc = mock_use_cases["project_plan_version_uc"]
        servicer.project_decision_uc = mock_use_cases["project_decision_uc"]
        servicer.record_milestone_uc = mock_use_cases["record_milestone_uc"]
        servicer.get_graph_relationships_uc = mock_use_cases["get_graph_relationships_uc"]
        servicer.process_context_change_uc = mock_use_cases["process_context_change_uc"]
        servicer.nats_handler = mock_nats_handler
        return servicer


class TestGetContext:
    """Test GetContext gRPC method."""

    @pytest.mark.asyncio
    async def test_get_context_success(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_rehydrator: MagicMock,
    ) -> None:
        """Test successful GetContext request."""
        # Arrange
        request = context_pb2.GetContextRequest(
            story_id="story-123",
            role="architect",
            phase="DESIGN",
        )

        # Mock prompt blocks
        mock_prompt_blocks = MagicMock()
        mock_prompt_blocks.system = "System prompt"
        mock_prompt_blocks.context = "Context content"
        mock_prompt_blocks.tools = "Tools content"

        with patch("services.context.server.build_prompt_blocks", return_value=mock_prompt_blocks), \
             patch("services.context.server.detect_scopes", return_value=["scope1", "scope2"]):
            # Act
            await servicer.GetContext(request, mock_grpc_context)

        # Assert
        assert response.context is not None
        assert response.token_count > 0
        assert len(response.scopes) == 2
        assert response.version is not None
        assert response.blocks.system == "System prompt"
        assert response.blocks.context == "Context content"
        assert response.blocks.tools == "Tools content"
        mock_grpc_context.set_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_context_with_subtask_id(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
    ) -> None:
        """Test GetContext with subtask_id."""
        # Arrange
        request = context_pb2.GetContextRequest(
            story_id="story-123",
            role="architect",
            phase="DESIGN",
            subtask_id="task-456",
        )

        mock_prompt_blocks = MagicMock()
        mock_prompt_blocks.system = "System"
        mock_prompt_blocks.context = "Context"
        mock_prompt_blocks.tools = "Tools"

        with patch("services.context.server.build_prompt_blocks", return_value=mock_prompt_blocks), \
             patch("services.context.server.detect_scopes", return_value=[]):
            # Act
            await servicer.GetContext(request, mock_grpc_context)

        # Assert
        assert response.context is not None
        mock_grpc_context.set_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_context_error(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
    ) -> None:
        """Test GetContext error handling."""
        # Arrange
        request = context_pb2.GetContextRequest(
            story_id="story-123",
            role="architect",
            phase="DESIGN",
        )

        with patch("services.context.server.build_prompt_blocks", side_effect=Exception("Test error")):
            # Act
            await servicer.GetContext(request, mock_grpc_context)

        # Assert
        mock_grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        mock_grpc_context.set_details.assert_called_once()
        assert "Failed to get context" in mock_grpc_context.set_details.call_args[0][0]


class TestUpdateContext:
    """Test UpdateContext gRPC method."""

    @pytest.mark.asyncio
    async def test_update_context_success(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_use_cases: dict[str, MagicMock],
        mock_nats_handler: MagicMock,
    ) -> None:
        """Test successful UpdateContext request."""
        # Arrange
        change = context_pb2.ContextChange(
            operation="CREATE",
            entity_type="Task",
            entity_id="task-123",
        )
        request = context_pb2.UpdateContextRequest(
            story_id="story-123",
            task_id="task-456",
            changes=[change],
        )

        mock_use_cases["process_context_change_uc"].execute = AsyncMock()

        # Act
        response = await servicer.UpdateContext(request, mock_grpc_context)

        # Assert
        assert response.version > 0
        assert response.hash is not None
        assert len(response.warnings) == 0
        mock_use_cases["process_context_change_uc"].execute.assert_awaited_once()
        mock_nats_handler.publish_context_updated.assert_awaited_once()
        mock_grpc_context.set_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_context_with_warnings(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_use_cases: dict[str, MagicMock],
    ) -> None:
        """Test UpdateContext with processing errors (warnings)."""
        # Arrange
        change = context_pb2.ContextChange(
            operation="CREATE",
            entity_type="Task",
            entity_id="task-123",
        )
        request = context_pb2.UpdateContextRequest(
            story_id="story-123",
            changes=[change],
        )

        mock_use_cases["process_context_change_uc"].execute = AsyncMock(
            side_effect=Exception("Processing error")
        )

        # Act
        response = await servicer.UpdateContext(request, mock_grpc_context)

        # Assert
        assert len(response.warnings) == 1
        assert "task-123" in response.warnings[0]
        mock_grpc_context.set_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_context_without_nats(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_use_cases: dict[str, MagicMock],
    ) -> None:
        """Test UpdateContext without NATS handler."""
        # Arrange
        servicer.nats_handler = None
        request = context_pb2.UpdateContextRequest(
            story_id="story-123",
            changes=[],
        )

        # Act
        response = await servicer.UpdateContext(request, mock_grpc_context)

        # Assert
        assert response.version > 0
        mock_grpc_context.set_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_context_error(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_use_cases: dict[str, MagicMock],
    ) -> None:
        """Test UpdateContext error handling."""
        # Arrange
        request = context_pb2.UpdateContextRequest(
            story_id="story-123",
            changes=[],
        )

        mock_use_cases["process_context_change_uc"].execute = AsyncMock(
            side_effect=Exception("Critical error")
        )

        with patch("services.context.server.time.time", side_effect=Exception("Time error")):
            # Act
            response = await servicer.UpdateContext(request, mock_grpc_context)

        # Assert
        mock_grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        mock_grpc_context.set_details.assert_called_once()


class TestRehydrateSession:
    """Test RehydrateSession gRPC method."""

    @pytest.mark.asyncio
    async def test_rehydrate_session_success(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_rehydrator: MagicMock,
    ) -> None:
        """Test successful RehydrateSession request."""
        # Arrange
        request = context_pb2.RehydrateSessionRequest(
            case_id="story-123",
            roles=["architect", "developer"],
            include_timeline=True,
            include_summaries=True,
            timeline_events=100,
            persist_bundle=True,
            ttl_seconds=7200,
        )

        mock_bundle = MagicMock()
        mock_bundle.packs = [MagicMock(), MagicMock()]
        mock_rehydrator.build.return_value = mock_bundle

        mock_response = context_pb2.RehydrateSessionResponse()
        with patch("services.context.server.RehydrationProtobufMapper.bundle_to_response", return_value=mock_response):
            # Act
            response = await servicer.RehydrateSession(request, mock_grpc_context)

        # Assert
        assert response == mock_response
        mock_rehydrator.build.assert_called_once()
        mock_grpc_context.set_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_rehydrate_session_defaults(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_rehydrator: MagicMock,
    ) -> None:
        """Test RehydrateSession with default values."""
        # Arrange
        request = context_pb2.RehydrateSessionRequest(
            case_id="story-123",
            roles=["architect"],
            timeline_events=0,  # Should default to 50
            ttl_seconds=0,  # Should default to 3600
        )

        mock_bundle = MagicMock()
        mock_bundle.packs = []
        mock_rehydrator.build.return_value = mock_bundle

        with patch("services.context.server.RehydrationProtobufMapper.bundle_to_response", return_value=context_pb2.RehydrateSessionResponse()):
            # Act
            await servicer.RehydrateSession(request, mock_grpc_context)

        # Assert
        call_args = mock_rehydrator.build.call_args[0][0]
        assert call_args.timeline_events == 50
        assert call_args.ttl_seconds == 3600

    @pytest.mark.asyncio
    async def test_rehydrate_session_error(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_rehydrator: MagicMock,
    ) -> None:
        """Test RehydrateSession error handling."""
        # Arrange
        request = context_pb2.RehydrateSessionRequest(
            case_id="story-123",
            roles=["architect"],
        )

        mock_rehydrator.build.side_effect = Exception("Rehydration error")

        # Act
        response = await servicer.RehydrateSession(request, mock_grpc_context)

        # Assert
        mock_grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        mock_grpc_context.set_details.assert_called_once()
        assert isinstance(response, context_pb2.RehydrateSessionResponse)


class TestValidateScope:
    """Test ValidateScope gRPC method."""

    @pytest.mark.asyncio
    async def test_validate_scope_allowed(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_policy: MagicMock,
    ) -> None:
        """Test ValidateScope with allowed scopes."""
        # Arrange
        request = context_pb2.ValidateScopeRequest(
            role="architect",
            phase="DESIGN",
            provided_scopes=["scope1", "scope2"],
        )

        scope_check = MagicMock()
        scope_check.allowed = True
        scope_check.missing = set()
        scope_check.extra = set()
        mock_policy.check.return_value = scope_check

        # Act
        response = await servicer.ValidateScope(request, mock_grpc_context)

        # Assert
        assert response.allowed is True
        assert len(response.missing) == 0
        assert len(response.extra) == 0
        mock_policy.check.assert_called_once()
        mock_grpc_context.set_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_scope_not_allowed(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_policy: MagicMock,
    ) -> None:
        """Test ValidateScope with missing scopes."""
        # Arrange
        request = context_pb2.ValidateScopeRequest(
            role="architect",
            phase="DESIGN",
            provided_scopes=["scope1"],
        )

        scope_check = MagicMock()
        scope_check.allowed = False
        scope_check.missing = {"scope2", "scope3"}
        scope_check.extra = set()
        mock_policy.check.return_value = scope_check

        # Act
        response = await servicer.ValidateScope(request, mock_grpc_context)

        # Assert
        assert response.allowed is False
        assert len(response.missing) == 2
        assert "scope2" in response.missing
        assert "scope3" in response.missing

    @pytest.mark.asyncio
    async def test_validate_scope_error(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_policy: MagicMock,
    ) -> None:
        """Test ValidateScope error handling."""
        # Arrange
        request = context_pb2.ValidateScopeRequest(
            role="architect",
            phase="DESIGN",
            provided_scopes=[],
        )

        mock_policy.check.side_effect = Exception("Policy error")

        # Act
        response = await servicer.ValidateScope(request, mock_grpc_context)

        # Assert
        assert response.allowed is False
        assert "Policy error" in response.reason
        mock_grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)


class TestCreateStory:
    """Test CreateStory gRPC method."""

    @pytest.mark.asyncio
    async def test_create_story_success(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_neo4j_command_store: MagicMock,
        mock_redis_client: MagicMock,
    ) -> None:
        """Test successful CreateStory request."""
        # Arrange
        request = context_pb2.CreateStoryRequest(
            story_id="story-123",
            title="Test Story",
            description="Test description",
            initial_phase="DESIGN",
        )

        # Act
        response = await servicer.CreateStory(request, mock_grpc_context)

        # Assert
        assert response.story_id == "story-123"
        assert response.context_id == "ctx-story-123"
        assert response.current_phase == "DESIGN"
        mock_neo4j_command_store.upsert_entity.assert_called_once()
        mock_redis_client.hset.assert_called_once()
        mock_grpc_context.set_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_story_default_phase(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
    ) -> None:
        """Test CreateStory with default phase."""
        # Arrange
        request = context_pb2.CreateStoryRequest(
            story_id="story-123",
            title="Test Story",
            description="Test description",
            # initial_phase not set, should default to "DESIGN"
        )

        # Act
        response = await servicer.CreateStory(request, mock_grpc_context)

        # Assert
        assert response.current_phase == "DESIGN"

    @pytest.mark.asyncio
    async def test_create_story_error(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_neo4j_command_store: MagicMock,
    ) -> None:
        """Test CreateStory error handling."""
        # Arrange
        request = context_pb2.CreateStoryRequest(
            story_id="story-123",
            title="Test Story",
        )

        mock_neo4j_command_store.upsert_entity.side_effect = Exception("Neo4j error")

        # Act
        response = await servicer.CreateStory(request, mock_grpc_context)

        # Assert
        mock_grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        mock_grpc_context.set_details.assert_called_once()
        assert isinstance(response, context_pb2.CreateStoryResponse)


class TestCreateTask:
    """Test CreateTask gRPC method."""

    @pytest.mark.asyncio
    async def test_create_task_success(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_neo4j_command_store: MagicMock,
        mock_redis_client: MagicMock,
    ) -> None:
        """Test successful CreateTask request."""
        # Arrange
        request = context_pb2.CreateTaskRequest(
            task_id="task-123",
            story_id="story-456",
            title="Test Task",
            description="Test description",
            role="architect",
            priority=1,
            estimated_hours=8,
            dependencies=[],
        )

        # Act
        response = await servicer.CreateTask(request, mock_grpc_context)

        # Assert
        assert response.task_id == "task-123"
        assert response.story_id == "story-456"
        assert response.status == "PENDING"
        mock_neo4j_command_store.upsert_entity.assert_called_once()
        mock_neo4j_command_store.relate.assert_called_once()  # BELONGS_TO relationship
        mock_redis_client.hset.assert_called_once()
        mock_grpc_context.set_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_task_with_dependencies(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_neo4j_command_store: MagicMock,
    ) -> None:
        """Test CreateTask with dependencies."""
        # Arrange
        request = context_pb2.CreateTaskRequest(
            task_id="task-123",
            story_id="story-456",
            title="Test Task",
            description="Test",
            role="architect",
            priority=1,
            estimated_hours=8,
            dependencies=["task-1", "task-2"],
        )

        # Act
        await servicer.CreateTask(request, mock_grpc_context)

        # Assert
        # Should create BELONGS_TO + 2 DEPENDS_ON relationships
        assert mock_neo4j_command_store.relate.call_count == 3

    @pytest.mark.asyncio
    async def test_create_task_error(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_neo4j_command_store: MagicMock,
    ) -> None:
        """Test CreateTask error handling."""
        # Arrange
        request = context_pb2.CreateTaskRequest(
            task_id="task-123",
            story_id="story-456",
            title="Test Task",
            description="Test",
            role="architect",
            priority=1,
            estimated_hours=8,
        )

        mock_neo4j_command_store.upsert_entity.side_effect = Exception("Neo4j error")

        # Act
        response = await servicer.CreateTask(request, mock_grpc_context)

        # Assert
        mock_grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        assert isinstance(response, context_pb2.CreateTaskResponse)


class TestAddProjectDecision:
    """Test AddProjectDecision gRPC method."""

    @pytest.mark.asyncio
    async def test_add_project_decision_success(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_use_cases: dict[str, MagicMock],
    ) -> None:
        """Test successful AddProjectDecision request."""
        # Arrange
        request = context_pb2.AddProjectDecisionRequest(
            story_id="story-123",
            decision_type="ARCHITECTURE",
            title="Test Decision",
            rationale="Test rationale",
            alternatives_considered="alt1, alt2",
        )
        request.metadata["role"] = "architect"
        request.metadata["winner"] = "agent-1"

        # Act
        response = await servicer.AddProjectDecision(request, mock_grpc_context)

        # Assert
        assert response.decision_id is not None
        assert response.decision_id.startswith("DEC-")
        mock_use_cases["project_decision_uc"].execute.assert_called_once()
        mock_grpc_context.set_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_project_decision_default_metadata(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_use_cases: dict[str, MagicMock],
    ) -> None:
        """Test AddProjectDecision with default metadata."""
        # Arrange
        request = context_pb2.AddProjectDecisionRequest(
            story_id="story-123",
            decision_type="ARCHITECTURE",
            title="Test Decision",
            rationale="Test rationale",
        )

        # Act
        await servicer.AddProjectDecision(request, mock_grpc_context)

        # Assert
        call_args = mock_use_cases["project_decision_uc"].execute.call_args[0][0]
        assert call_args["made_by_role"] == "UNKNOWN"
        assert call_args["made_by_agent"] == "UNKNOWN"

    @pytest.mark.asyncio
    async def test_add_project_decision_error(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_use_cases: dict[str, MagicMock],
    ) -> None:
        """Test AddProjectDecision error handling."""
        # Arrange
        request = context_pb2.AddProjectDecisionRequest(
            story_id="story-123",
            decision_type="ARCHITECTURE",
            title="Test Decision",
            rationale="Test",
        )

        mock_use_cases["project_decision_uc"].execute.side_effect = Exception("Use case error")

        # Act
        response = await servicer.AddProjectDecision(request, mock_grpc_context)

        # Assert
        mock_grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        assert isinstance(response, context_pb2.AddProjectDecisionResponse)


class TestTransitionPhase:
    """Test TransitionPhase gRPC method."""

    @pytest.mark.asyncio
    async def test_transition_phase_success(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_neo4j_command_store: MagicMock,
    ) -> None:
        """Test successful TransitionPhase request."""
        # Arrange
        request = context_pb2.TransitionPhaseRequest(
            story_id="story-123",
            from_phase="DESIGN",
            to_phase="BUILD",
            rationale="Moving to build phase",
        )

        # Act
        response = await servicer.TransitionPhase(request, mock_grpc_context)

        # Assert
        assert response.story_id == "story-123"
        assert response.current_phase == "BUILD"
        assert response.transitioned_at is not None
        mock_neo4j_command_store.execute_write.assert_called_once()
        mock_grpc_context.set_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_transition_phase_error(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_neo4j_command_store: MagicMock,
    ) -> None:
        """Test TransitionPhase error handling."""
        # Arrange
        request = context_pb2.TransitionPhaseRequest(
            story_id="story-123",
            from_phase="DESIGN",
            to_phase="BUILD",
            rationale="Test",
        )

        mock_neo4j_command_store.execute_write.side_effect = Exception("Neo4j error")

        # Act
        response = await servicer.TransitionPhase(request, mock_grpc_context)

        # Assert
        mock_grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        assert isinstance(response, context_pb2.TransitionPhaseResponse)


class TestGetGraphRelationships:
    """Test GetGraphRelationships gRPC method."""

    @pytest.mark.asyncio
    async def test_get_graph_relationships_success(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_use_cases: dict[str, MagicMock],
    ) -> None:
        """Test successful GetGraphRelationships request."""
        # Arrange
        request = context_pb2.GetGraphRelationshipsRequest(
            node_id="project-1",
            node_type="Project",
            depth=2,
        )

        mock_result = MagicMock()
        mock_result.node = MagicMock()
        mock_result.node.id = "project-1"
        mock_result.neighbors = [MagicMock(), MagicMock()]
        mock_result.relationships = [MagicMock()]
        mock_use_cases["get_graph_relationships_uc"].execute.return_value = mock_result

        mock_protobuf_response = context_pb2.GetGraphRelationshipsResponse()
        with patch("services.context.server.GraphRelationshipsProtobufMapper.to_protobuf_response", return_value=mock_protobuf_response):
            # Act
            response = await servicer.GetGraphRelationships(request, mock_grpc_context)

        # Assert
        assert response == mock_protobuf_response
        mock_use_cases["get_graph_relationships_uc"].execute.assert_called_once_with(
            "project-1",
            "Project",
            2,
        )
        mock_grpc_context.set_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_graph_relationships_depth_clamping(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_use_cases: dict[str, MagicMock],
    ) -> None:
        """Test GetGraphRelationships depth clamping."""
        # Arrange
        request = context_pb2.GetGraphRelationshipsRequest(
            node_id="project-1",
            node_type="Project",
            depth=5,  # Should be clamped to 3
        )

        mock_result = MagicMock()
        mock_result.node = MagicMock()
        mock_result.node.id = "project-1"
        mock_result.neighbors = []
        mock_result.relationships = []
        mock_use_cases["get_graph_relationships_uc"].execute.return_value = mock_result

        with patch("services.context.server.GraphRelationshipsProtobufMapper.to_protobuf_response", return_value=context_pb2.GetGraphRelationshipsResponse()):
            # Act
            await servicer.GetGraphRelationships(request, mock_grpc_context)

        # Assert
        # Depth should be clamped to 3
        call_args = mock_use_cases["get_graph_relationships_uc"].execute.call_args[0]
        assert call_args[2] == 3  # depth parameter

    @pytest.mark.asyncio
    async def test_get_graph_relationships_validation_error(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_use_cases: dict[str, MagicMock],
    ) -> None:
        """Test GetGraphRelationships with ValueError."""
        # Arrange
        request = context_pb2.GetGraphRelationshipsRequest(
            node_id="invalid",
            node_type="InvalidType",
            depth=1,
        )

        mock_use_cases["get_graph_relationships_uc"].execute.side_effect = ValueError("Invalid node type")

        mock_error_response = context_pb2.GetGraphRelationshipsResponse()
        with patch("services.context.server.GraphRelationshipsProtobufMapper.to_error_response", return_value=mock_error_response):
            # Act
            response = await servicer.GetGraphRelationships(request, mock_grpc_context)

        # Assert
        mock_grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)
        assert response == mock_error_response

    @pytest.mark.asyncio
    async def test_get_graph_relationships_general_error(
        self,
        servicer: ContextServiceServicer,
        mock_grpc_context: MagicMock,
        mock_use_cases: dict[str, MagicMock],
    ) -> None:
        """Test GetGraphRelationships with general error."""
        # Arrange
        request = context_pb2.GetGraphRelationshipsRequest(
            node_id="project-1",
            node_type="Project",
            depth=1,
        )

        mock_use_cases["get_graph_relationships_uc"].execute.side_effect = Exception("Database error")

        mock_error_response = context_pb2.GetGraphRelationshipsResponse()
        with patch("services.context.server.GraphRelationshipsProtobufMapper.to_error_response", return_value=mock_error_response):
            # Act
            response = await servicer.GetGraphRelationships(request, mock_grpc_context)

        # Assert
        mock_grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        assert response == mock_error_response


class TestHelperMethods:
    """Test helper methods of ContextServiceServicer."""

    def test_serialize_prompt_blocks_all_sections(
        self,
        servicer: ContextServiceServicer,
    ) -> None:
        """Test _serialize_prompt_blocks with all sections."""
        # Arrange
        prompt_blocks = MagicMock()
        prompt_blocks.system = "System content"
        prompt_blocks.context = "Context content"
        prompt_blocks.tools = "Tools content"

        # Act
        result = servicer._serialize_prompt_blocks(prompt_blocks)

        # Assert
        assert "System content" in result
        assert "Context content" in result
        assert "Tools content" in result
        assert "---" in result

    def test_serialize_prompt_blocks_partial(
        self,
        servicer: ContextServiceServicer,
    ) -> None:
        """Test _serialize_prompt_blocks with partial sections."""
        # Arrange
        prompt_blocks = MagicMock()
        prompt_blocks.system = "System content"
        prompt_blocks.context = ""
        prompt_blocks.tools = None

        # Act
        result = servicer._serialize_prompt_blocks(prompt_blocks)

        # Assert
        assert "System content" in result
        assert "Context" not in result
        assert "Tools" not in result

    def test_serialize_prompt_blocks_empty_context(
        self,
        servicer: ContextServiceServicer,
    ) -> None:
        """Test _serialize_prompt_blocks with empty context string."""
        # Arrange
        prompt_blocks = MagicMock()
        prompt_blocks.system = "System"
        prompt_blocks.context = ""  # Empty string (falsy but not None)
        prompt_blocks.tools = "Tools"

        # Act
        result = servicer._serialize_prompt_blocks(prompt_blocks)

        # Assert
        assert "System" in result
        assert "Tools" in result
        # Context section should not appear when empty
        assert "# Context" not in result or result.count("# Context") == 0

    def test_generate_version_hash(
        self,
        servicer: ContextServiceServicer,
    ) -> None:
        """Test _generate_version_hash."""
        # Arrange
        content = "test content"

        # Act
        result = servicer._generate_version_hash(content)

        # Assert
        assert len(result) == 16
        assert isinstance(result, str)

    def test_generate_new_version(
        self,
        servicer: ContextServiceServicer,
    ) -> None:
        """Test _generate_new_version."""
        # Arrange
        story_id = "story-123"

        # Act
        result = servicer._generate_new_version(story_id)

        # Assert
        assert isinstance(result, int)
        assert result > 0

    def test_generate_context_hash(
        self,
        servicer: ContextServiceServicer,
    ) -> None:
        """Test _generate_context_hash."""
        # Arrange
        story_id = "story-123"
        version = 1234567890

        # Act
        result = servicer._generate_context_hash(story_id, version)

        # Assert
        assert len(result) == 16
        assert isinstance(result, str)

    def test_format_scope_reason_allowed(
        self,
        servicer: ContextServiceServicer,
    ) -> None:
        """Test _format_scope_reason with allowed scopes."""
        # Arrange
        scope_check = MagicMock()
        scope_check.allowed = True
        scope_check.missing = set()
        scope_check.extra = set()

        # Act
        result = servicer._format_scope_reason(scope_check)

        # Assert
        assert result == "All scopes are allowed"

    def test_format_scope_reason_missing(
        self,
        servicer: ContextServiceServicer,
    ) -> None:
        """Test _format_scope_reason with missing scopes."""
        # Arrange
        scope_check = MagicMock()
        scope_check.allowed = False
        scope_check.missing = {"scope1", "scope2"}
        scope_check.extra = set()

        # Act
        result = servicer._format_scope_reason(scope_check)

        # Assert
        assert "Missing required scopes" in result
        assert "scope1" in result
        assert "scope2" in result

    def test_format_scope_reason_extra(
        self,
        servicer: ContextServiceServicer,
    ) -> None:
        """Test _format_scope_reason with extra scopes."""
        # Arrange
        scope_check = MagicMock()
        scope_check.allowed = False
        scope_check.missing = set()
        scope_check.extra = {"scope3", "scope4"}

        # Act
        result = servicer._format_scope_reason(scope_check)

        # Assert
        assert "Extra scopes not allowed" in result
        assert "scope3" in result
        assert "scope4" in result

    def test_handle_nats_publish_error_success(
        self,
        servicer: ContextServiceServicer,
    ) -> None:
        """Test _handle_nats_publish_error with successful task."""
        # Arrange
        mock_task = MagicMock()
        mock_task.result.return_value = None

        # Act
        servicer._handle_nats_publish_error(mock_task)

        # Assert
        mock_task.result.assert_called_once()

    def test_handle_nats_publish_error_failure(
        self,
        servicer: ContextServiceServicer,
    ) -> None:
        """Test _handle_nats_publish_error with failed task."""
        # Arrange
        mock_task = MagicMock()
        mock_task.result.side_effect = Exception("NATS error")

        # Act
        servicer._handle_nats_publish_error(mock_task)

        # Assert
        mock_task.result.assert_called_once()

    def test_detect_scopes(
        self,
        servicer: ContextServiceServicer,
    ) -> None:
        """Test _detect_scopes delegates to detect_scopes utility."""
        # Arrange
        prompt_blocks = MagicMock()

        with patch("services.context.server.detect_scopes", return_value=["scope1", "scope2"]) as mock_detect:
            # Act
            result = servicer._detect_scopes(prompt_blocks)

        # Assert
        assert result == ["scope1", "scope2"]
        mock_detect.assert_called_once_with(prompt_blocks)

    def test_bundle_to_proto(
        self,
        servicer: ContextServiceServicer,
    ) -> None:
        """Test _bundle_to_proto delegates to mapper."""
        # Arrange
        mock_bundle = MagicMock()
        mock_response = context_pb2.RehydrateSessionResponse()

        with patch("services.context.server.RehydrationProtobufMapper.bundle_to_response", return_value=mock_response) as mock_mapper:
            # Act
            result = servicer._bundle_to_proto(mock_bundle)

        # Assert
        assert result == mock_response
        mock_mapper.assert_called_once_with(mock_bundle)

