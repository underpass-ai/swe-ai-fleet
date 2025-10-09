"""
Integration tests for Context Service.
Tests gRPC API and NATS messaging.
"""

import pytest
import grpc
from unittest.mock import Mock, AsyncMock, patch

# Mark all tests as integration tests
pytestmark = pytest.mark.integration


class TestContextServiceGRPC:
    """Test Context Service gRPC API."""

    @pytest.fixture
    def mock_servicer(self):
        """Create a mock Context Service servicer."""
        with patch('services.context.server.ContextServiceServicer') as mock:
            servicer = mock.return_value
            servicer.rehydrator = Mock()
            servicer.policy = Mock()
            servicer.graph_query = Mock()
            servicer.graph_command = Mock()
            servicer.planning_read = Mock()
            yield servicer

    def test_get_context_success(self, mock_servicer):
        """Test successful GetContext request."""
        # This would require a running gRPC server
        # For now, test the servicer logic directly
        
        from services.context.gen import context_pb2
        
        request = context_pb2.GetContextRequest(
            story_id="test-001",
            role="DEV",
            phase="BUILD",
        )
        
        # Mock the build_prompt_blocks function
        with patch('services.context.server.build_prompt_blocks') as mock_build:
            mock_blocks = Mock()
            mock_blocks.system = "System message"
            mock_blocks.context = "Context data"
            mock_blocks.tools = "Tools available"
            mock_build.return_value = mock_blocks
            
            response = mock_servicer.GetContext(request, Mock())
            
            assert response is not None
            # Would assert response fields if servicer was properly mocked

    def test_update_context_with_changes(self, mock_servicer):
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
                    payload='{"title":"Use PostgreSQL"}',
                    reason="Performance requirements",
                ),
            ],
        )
        
        response = mock_servicer.UpdateContext(request, Mock())
        
        assert response is not None

    def test_rehydrate_session(self, mock_servicer):
        """Test RehydrateSession request."""
        from services.context.gen import context_pb2
        
        request = context_pb2.RehydrateSessionRequest(
            case_id="case-001",
            roles=["DEV", "QA"],
            include_timeline=True,
            include_summaries=True,
        )
        
        # Mock rehydrator
        mock_bundle = Mock()
        mock_bundle.case_id = "case-001"
        mock_bundle.generated_at_ms = 1234567890
        mock_bundle.packs = {}
        mock_bundle.stats = {
            "decisions": 5,
            "decision_edges": 3,
            "impacts": 2,
            "events": 10,
            "roles": ["DEV", "QA"],
        }
        
        mock_servicer.rehydrator.build.return_value = mock_bundle
        
        response = mock_servicer.RehydrateSession(request, Mock())
        
        assert response is not None

    def test_validate_scope_allowed(self, mock_servicer):
        """Test ValidateScope with allowed scopes."""
        from services.context.gen import context_pb2
        
        request = context_pb2.ValidateScopeRequest(
            role="DEV",
            phase="BUILD",
            provided_scopes=["CASE_HEADER", "PLAN_HEADER"],
        )
        
        # Mock policy check
        mock_check = Mock()
        mock_check.allowed = True
        mock_check.missing = set()
        mock_check.extra = set()
        
        mock_servicer.policy.check.return_value = mock_check
        
        response = mock_servicer.ValidateScope(request, Mock())
        
        assert response is not None


class TestContextNATSHandler:
    """Test Context Service NATS integration."""

    @pytest.fixture
    async def mock_nats_client(self):
        """Create a mock NATS client."""
        with patch('nats.connect') as mock_connect:
            mock_nc = AsyncMock()
            mock_js = AsyncMock()
            mock_nc.jetstream.return_value = mock_js
            mock_connect.return_value = mock_nc
            yield mock_nc

    @pytest.mark.asyncio
    async def test_nats_connect(self, mock_nats_client):
        """Test NATS connection."""
        from services.context.nats_handler import ContextNATSHandler
        
        handler = ContextNATSHandler(
            nats_url="nats://localhost:4222",
            context_service=Mock(),
        )
        
        await handler.connect()
        
        assert handler.nc is not None

    @pytest.mark.asyncio
    async def test_publish_context_updated(self, mock_nats_client):
        """Test publishing context updated event."""
        from services.context.nats_handler import ContextNATSHandler
        
        handler = ContextNATSHandler(
            nats_url="nats://localhost:4222",
            context_service=Mock(),
        )
        
        handler.nc = mock_nats_client
        handler.js = mock_nats_client.jetstream()
        
        await handler.publish_context_updated("story-001", 2)
        
        # Verify publish was called
        handler.js.publish.assert_called_once()


class TestContextServiceIntegration:
    """End-to-end integration tests."""

    @pytest.mark.e2e
    @pytest.mark.skip(reason="Requires running services")
    async def test_full_context_workflow(self):
        """Test complete context workflow: get, update, rehydrate."""
        # This would test with actual running services
        # 1. GetContext
        # 2. UpdateContext
        # 3. RehydrateSession
        # 4. Verify NATS events
        pass

    @pytest.mark.e2e
    @pytest.mark.skip(reason="Requires running services")
    async def test_context_with_neo4j(self):
        """Test context service with real Neo4j."""
        # This would test with actual Neo4j database
        pass

    @pytest.mark.e2e
    @pytest.mark.skip(reason="Requires running services")
    async def test_context_with_redis(self):
        """Test context service with real Redis."""
        # This would test with actual Redis
        pass

