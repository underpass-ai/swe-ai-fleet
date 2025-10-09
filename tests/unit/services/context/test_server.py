"""
Unit tests for Context Service gRPC server.
"""

from unittest.mock import AsyncMock, Mock, patch

import grpc
import pytest

# Mark all tests as unit tests
pytestmark = pytest.mark.unit

# Test fixtures - mock connection values (not real credentials)
TEST_NEO4J_URI = "bolt://test:7687"
TEST_NEO4J_USER = "test"
TEST_NEO4J_AUTH = "test"  # Mock auth token for unit tests
TEST_REDIS_HOST = "test"
TEST_REDIS_PORT = 6379


@pytest.fixture
def mock_neo4j_query():
    """Mock Neo4j query store."""
    mock = Mock()
    mock.get_plan_by_case = Mock(return_value=None)
    mock.list_decisions = Mock(return_value=[])
    mock.list_decision_dependencies = Mock(return_value=[])
    mock.list_decision_impacts = Mock(return_value=[])
    return mock


@pytest.fixture
def mock_neo4j_command():
    """Mock Neo4j command store."""
    return Mock()


@pytest.fixture
def mock_redis_planning():
    """Mock Redis planning adapter."""
    mock = Mock()
    mock.get_case_spec = Mock(return_value=None)
    mock.get_plan_draft = Mock(return_value=None)
    mock.get_planning_events = Mock(return_value=[])
    return mock


@pytest.fixture
def mock_rehydrator(mock_redis_planning, mock_neo4j_query):
    """Mock SessionRehydrationUseCase."""
    with patch('services.context.server.SessionRehydrationUseCase') as mock_class:
        mock_instance = mock_class.return_value
        mock_instance.build = Mock()
        yield mock_instance


@pytest.fixture
def mock_policy():
    """Mock PromptScopePolicy."""
    with patch('services.context.server.PromptScopePolicy') as mock_class:
        mock_instance = mock_class.return_value
        mock_instance.check = Mock()
        mock_instance.redact = Mock(side_effect=lambda role, text: text)
        yield mock_instance


@pytest.fixture
def mock_prompt_blocks():
    """Mock PromptBlocks."""
    mock = Mock()
    mock.system = "You are a DEV agent"
    mock.context = "Case: Test case\nPlan: Test plan"
    mock.tools = "Available tools: git, docker"
    return mock


@pytest.fixture
def context_servicer(mock_neo4j_query, mock_neo4j_command, mock_redis_planning):
    """Create ContextServiceServicer with mocked dependencies."""
    with (
        patch('services.context.server.Neo4jGraphQueryStore', return_value=mock_neo4j_query),
        patch('services.context.server.Neo4jGraphCommandStore', return_value=mock_neo4j_command),
        patch('services.context.server.RedisPlanningReadAdapter', return_value=mock_redis_planning),
        patch('services.context.server.SessionRehydrationUseCase'),
        patch('services.context.server.PromptScopePolicy'),
    ):
        from services.context.server import ContextServiceServicer

        servicer = ContextServiceServicer(
            neo4j_uri=TEST_NEO4J_URI,
            neo4j_user=TEST_NEO4J_USER,
            neo4j_password=TEST_NEO4J_AUTH,
            redis_host=TEST_REDIS_HOST,
            redis_port=TEST_REDIS_PORT,
            nats_handler=None,
        )

        yield servicer


class TestGetContext:
    """Test GetContext gRPC method."""

    def test_get_context_success(self, context_servicer, mock_prompt_blocks):
        """Test successful GetContext request."""
        from services.context.gen import context_pb2

        request = context_pb2.GetContextRequest(
            story_id="test-001",
            role="DEV",
            phase="BUILD",
        )

        grpc_context = Mock()

        with patch('services.context.server.build_prompt_blocks', return_value=mock_prompt_blocks):
            response = context_servicer.GetContext(request, grpc_context)

        assert response is not None
        assert isinstance(response, context_pb2.GetContextResponse)
        assert response.token_count > 0
        assert response.blocks.system == "You are a DEV agent"
        assert "Test case" in response.context

    def test_get_context_with_subtask(self, context_servicer, mock_prompt_blocks):
        """Test GetContext with specific subtask."""
        from services.context.gen import context_pb2

        request = context_pb2.GetContextRequest(
            story_id="test-001",
            role="DEV",
            phase="BUILD",
            subtask_id="task-001",
        )

        grpc_context = Mock()

        with patch(
            'services.context.server.build_prompt_blocks', return_value=mock_prompt_blocks
        ) as mock_build:
            response = context_servicer.GetContext(request, grpc_context)

        # Verify subtask_id was passed
        mock_build.assert_called_once()
        call_kwargs = mock_build.call_args[1]
        assert call_kwargs['current_subtask_id'] == "task-001"

        assert response is not None

    def test_get_context_error_handling(self, context_servicer):
        """Test GetContext error handling."""
        from services.context.gen import context_pb2

        request = context_pb2.GetContextRequest(
            story_id="test-001",
            role="DEV",
            phase="BUILD",
        )

        grpc_context = Mock()

        with patch('services.context.server.build_prompt_blocks', side_effect=Exception("Test error")):
            response = context_servicer.GetContext(request, grpc_context)

        # Should set error code
        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        grpc_context.set_details.assert_called_once()

        # Should return empty response
        assert response is not None

    def test_serialize_prompt_blocks(self, context_servicer, mock_prompt_blocks):
        """Test _serialize_prompt_blocks method."""
        result = context_servicer._serialize_prompt_blocks(mock_prompt_blocks)

        assert "# System" in result
        assert "You are a DEV agent" in result
        assert "# Context" in result
        assert "Test case" in result
        assert "# Tools" in result

    def test_generate_version_hash(self, context_servicer):
        """Test _generate_version_hash method."""
        content = "test content"
        hash1 = context_servicer._generate_version_hash(content)
        hash2 = context_servicer._generate_version_hash(content)

        # Same content should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 16  # SHA256 truncated to 16 chars

        # Different content should produce different hash
        hash3 = context_servicer._generate_version_hash("different content")
        assert hash1 != hash3


class TestUpdateContext:
    """Test UpdateContext gRPC method."""

    def test_update_context_success(self, context_servicer):
        """Test successful UpdateContext request."""
        from services.context.gen import context_pb2

        request = context_pb2.UpdateContextRequest(
            story_id="test-001",
            task_id="task-001",
            role="DEV",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="DECISION",
                    entity_id="dec-001",
                    payload='{"title":"Use PostgreSQL"}',
                    reason="Performance requirements",
                ),
            ],
        )

        grpc_context = Mock()

        response = context_servicer.UpdateContext(request, grpc_context)

        assert response is not None
        assert isinstance(response, context_pb2.UpdateContextResponse)
        assert response.version > 0
        assert len(response.hash) > 0

    def test_update_context_multiple_changes(self, context_servicer):
        """Test UpdateContext with multiple changes."""
        from services.context.gen import context_pb2

        request = context_pb2.UpdateContextRequest(
            story_id="test-001",
            task_id="task-001",
            role="DEV",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="DECISION",
                    entity_id="dec-001",
                    payload='{"title":"Decision 1"}',
                    reason="Reason 1",
                ),
                context_pb2.ContextChange(
                    operation="UPDATE",
                    entity_type="SUBTASK",
                    entity_id="task-001",
                    payload='{"status":"completed"}',
                    reason="Task completed",
                ),
            ],
        )

        grpc_context = Mock()

        response = context_servicer.UpdateContext(request, grpc_context)

        assert response is not None
        assert response.version > 0

    def test_update_context_with_nats(self, context_servicer):
        """Test UpdateContext publishes NATS event."""
        from services.context.gen import context_pb2

        # Add mock NATS handler
        mock_nats = AsyncMock()
        context_servicer.nats_handler = mock_nats

        request = context_pb2.UpdateContextRequest(
            story_id="test-001",
            task_id="task-001",
            role="DEV",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="DECISION",
                    entity_id="dec-001",
                    payload='{}',
                    reason="Test",
                ),
            ],
        )

        grpc_context = Mock()

        with patch('asyncio.create_task') as mock_create_task:
            response = context_servicer.UpdateContext(request, grpc_context)

        # Should create async task for NATS publish
        mock_create_task.assert_called_once()

        assert response is not None

    def test_update_context_error_handling(self, context_servicer):
        """Test UpdateContext error handling."""
        from services.context.gen import context_pb2

        request = context_pb2.UpdateContextRequest(
            story_id="test-001",
            task_id="task-001",
            role="DEV",
            changes=[],
        )

        grpc_context = Mock()

        with patch.object(context_servicer, '_generate_new_version', side_effect=Exception("Test error")):
            response = context_servicer.UpdateContext(request, grpc_context)

        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        assert response is not None


class TestRehydrateSession:
    """Test RehydrateSession gRPC method."""

    def test_rehydrate_session_success(self, context_servicer):
        """Test successful RehydrateSession request."""
        from services.context.gen import context_pb2

        # Mock rehydration bundle
        mock_bundle = Mock()
        mock_bundle.case_id = "case-001"
        mock_bundle.generated_at_ms = 1234567890
        mock_bundle.packs = {
            "DEV": Mock(
                role="DEV",
                case_header={
                    "case_id": "case-001",
                    "title": "Test",
                    "description": "",
                    "status": "ACTIVE",
                    "created_at": "",
                    "created_by": "",
                },
                plan_header={
                    "plan_id": "plan-001",
                    "version": 1,
                    "status": "ACTIVE",
                    "total_subtasks": 0,
                    "completed_subtasks": 0,
                },
                role_subtasks=[],
                decisions_relevant=[],
                decision_dependencies=[],
                impacted_subtasks=[],
                recent_milestones=[],
                last_summary="",
                token_budget_hint=4096,
            )
        }
        mock_bundle.stats = {
            "decisions": 5,
            "decision_edges": 3,
            "impacts": 2,
            "events": 10,
            "roles": ["DEV"],
        }

        context_servicer.rehydrator.build = Mock(return_value=mock_bundle)

        request = context_pb2.RehydrateSessionRequest(
            case_id="case-001",
            roles=["DEV"],
            include_timeline=True,
            include_summaries=True,
        )

        grpc_context = Mock()

        response = context_servicer.RehydrateSession(request, grpc_context)

        assert response is not None
        assert isinstance(response, context_pb2.RehydrateSessionResponse)
        assert response.case_id == "case-001"
        assert len(response.packs) == 1
        assert "DEV" in response.packs

    def test_rehydrate_session_multiple_roles(self, context_servicer):
        """Test RehydrateSession with multiple roles."""
        from services.context.gen import context_pb2

        mock_bundle = Mock()
        mock_bundle.case_id = "case-001"
        mock_bundle.generated_at_ms = 1234567890
        mock_bundle.packs = {
            "DEV": Mock(
                role="DEV",
                case_header={
                    "case_id": "case-001",
                    "title": "Test",
                    "description": "",
                    "status": "ACTIVE",
                    "created_at": "",
                    "created_by": "",
                },
                plan_header={
                    "plan_id": "plan-001",
                    "version": 1,
                    "status": "ACTIVE",
                    "total_subtasks": 0,
                    "completed_subtasks": 0,
                },
                role_subtasks=[],
                decisions_relevant=[],
                decision_dependencies=[],
                impacted_subtasks=[],
                recent_milestones=[],
                last_summary="",
                token_budget_hint=4096,
            ),
            "QA": Mock(
                role="QA",
                case_header={
                    "case_id": "case-001",
                    "title": "Test",
                    "description": "",
                    "status": "ACTIVE",
                    "created_at": "",
                    "created_by": "",
                },
                plan_header={
                    "plan_id": "plan-001",
                    "version": 1,
                    "status": "ACTIVE",
                    "total_subtasks": 0,
                    "completed_subtasks": 0,
                },
                role_subtasks=[],
                decisions_relevant=[],
                decision_dependencies=[],
                impacted_subtasks=[],
                recent_milestones=[],
                last_summary="",
                token_budget_hint=4096,
            ),
        }
        mock_bundle.stats = {
            "decisions": 5,
            "decision_edges": 3,
            "impacts": 2,
            "events": 10,
            "roles": ["DEV", "QA"],
        }

        context_servicer.rehydrator.build = Mock(return_value=mock_bundle)

        request = context_pb2.RehydrateSessionRequest(
            case_id="case-001",
            roles=["DEV", "QA"],
            include_timeline=True,
        )

        grpc_context = Mock()

        response = context_servicer.RehydrateSession(request, grpc_context)

        assert len(response.packs) == 2
        assert "DEV" in response.packs
        assert "QA" in response.packs

    def test_rehydrate_session_error_handling(self, context_servicer):
        """Test RehydrateSession error handling."""
        from services.context.gen import context_pb2

        context_servicer.rehydrator.build = Mock(side_effect=Exception("Test error"))

        request = context_pb2.RehydrateSessionRequest(
            case_id="case-001",
            roles=["DEV"],
        )

        grpc_context = Mock()

        response = context_servicer.RehydrateSession(request, grpc_context)

        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        assert response is not None


class TestValidateScope:
    """Test ValidateScope gRPC method."""

    def test_validate_scope_allowed(self, context_servicer):
        """Test ValidateScope with allowed scopes."""
        from services.context.gen import context_pb2

        mock_check = Mock()
        mock_check.allowed = True
        mock_check.missing = set()
        mock_check.extra = set()

        context_servicer.policy.check = Mock(return_value=mock_check)

        request = context_pb2.ValidateScopeRequest(
            role="DEV",
            phase="BUILD",
            provided_scopes=["CASE_HEADER", "PLAN_HEADER"],
        )

        grpc_context = Mock()

        response = context_servicer.ValidateScope(request, grpc_context)

        assert response is not None
        assert isinstance(response, context_pb2.ValidateScopeResponse)
        assert response.allowed is True
        assert len(response.missing) == 0
        assert len(response.extra) == 0

    def test_validate_scope_missing_scopes(self, context_servicer):
        """Test ValidateScope with missing required scopes."""
        from services.context.gen import context_pb2

        mock_check = Mock()
        mock_check.allowed = False
        mock_check.missing = {"SUBTASKS_ROLE"}
        mock_check.extra = set()

        context_servicer.policy.check = Mock(return_value=mock_check)

        request = context_pb2.ValidateScopeRequest(
            role="DEV",
            phase="BUILD",
            provided_scopes=["CASE_HEADER"],
        )

        grpc_context = Mock()

        response = context_servicer.ValidateScope(request, grpc_context)

        assert response.allowed is False
        assert "SUBTASKS_ROLE" in response.missing
        assert "Missing required scopes" in response.reason

    def test_validate_scope_extra_scopes(self, context_servicer):
        """Test ValidateScope with extra not-allowed scopes."""
        from services.context.gen import context_pb2

        mock_check = Mock()
        mock_check.allowed = False
        mock_check.missing = set()
        mock_check.extra = {"SUBTASKS_ALL"}

        context_servicer.policy.check = Mock(return_value=mock_check)

        request = context_pb2.ValidateScopeRequest(
            role="DEV",
            phase="BUILD",
            provided_scopes=["CASE_HEADER", "SUBTASKS_ALL"],
        )

        grpc_context = Mock()

        response = context_servicer.ValidateScope(request, grpc_context)

        assert response.allowed is False
        assert "SUBTASKS_ALL" in response.extra
        assert "Extra scopes not allowed" in response.reason

    def test_validate_scope_error_handling(self, context_servicer):
        """Test ValidateScope error handling."""
        from services.context.gen import context_pb2

        context_servicer.policy.check = Mock(side_effect=Exception("Test error"))

        request = context_pb2.ValidateScopeRequest(
            role="DEV",
            phase="BUILD",
            provided_scopes=[],
        )

        grpc_context = Mock()

        response = context_servicer.ValidateScope(request, grpc_context)

        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        assert response.allowed is False
        assert "Test error" in response.reason


class TestHelperMethods:
    """Test helper methods."""

    def test_detect_scopes(self, context_servicer, mock_prompt_blocks):
        """Test _detect_scopes method."""
        scopes = context_servicer._detect_scopes(mock_prompt_blocks)

        # Currently returns empty list
        assert isinstance(scopes, list)

    def test_generate_context_hash(self, context_servicer):
        """Test _generate_context_hash method."""
        hash1 = context_servicer._generate_context_hash("story-001", 1)
        hash2 = context_servicer._generate_context_hash("story-001", 1)

        # Same inputs should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 16

        # Different version should produce different hash
        hash3 = context_servicer._generate_context_hash("story-001", 2)
        assert hash1 != hash3

    def test_format_scope_reason(self, context_servicer):
        """Test _format_scope_reason method."""
        # Allowed case
        mock_check = Mock()
        mock_check.allowed = True
        mock_check.missing = set()
        mock_check.extra = set()

        reason = context_servicer._format_scope_reason(mock_check)
        assert "allowed" in reason.lower()

        # Missing scopes
        mock_check.allowed = False
        mock_check.missing = {"SCOPE1", "SCOPE2"}
        mock_check.extra = set()

        reason = context_servicer._format_scope_reason(mock_check)
        assert "Missing" in reason
        assert "SCOPE1" in reason

        # Extra scopes
        mock_check.missing = set()
        mock_check.extra = {"SCOPE3"}

        reason = context_servicer._format_scope_reason(mock_check)
        assert "Extra" in reason
        assert "SCOPE3" in reason
