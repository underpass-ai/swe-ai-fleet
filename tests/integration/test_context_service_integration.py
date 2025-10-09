"""
Integration tests for Context Service.
Tests with real gRPC server, mocked backends, and NATS.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Mark all tests as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def grpc_channel():
    """Create gRPC channel for testing."""
    # This would connect to a real server in full integration tests
    # For now, we'll mock it
    return Mock()


@pytest.fixture
async def mock_nats_client():
    """Create mock NATS client for testing."""
    mock_nc = AsyncMock()
    mock_js = AsyncMock()
    mock_nc.jetstream.return_value = mock_js
    return mock_nc


class TestContextServiceGRPCIntegration:
    """Integration tests for gRPC API."""

    @pytest.mark.skip(reason="Requires running gRPC server")
    def test_get_context_end_to_end(self, grpc_channel):
        """Test GetContext end-to-end with real server."""
        from services.context.gen import context_pb2, context_pb2_grpc
        
        stub = context_pb2_grpc.ContextServiceStub(grpc_channel)
        
        request = context_pb2.GetContextRequest(
            story_id="USR-001",
            role="DEV",
            phase="BUILD",
        )
        
        response = stub.GetContext(request)
        
        assert response is not None
        assert response.token_count > 0
        assert len(response.context) > 0
        assert response.blocks.system
        assert response.blocks.context

    @pytest.mark.skip(reason="Requires running gRPC server")
    def test_update_context_end_to_end(self, grpc_channel):
        """Test UpdateContext end-to-end with real server."""
        from services.context.gen import context_pb2, context_pb2_grpc
        
        stub = context_pb2_grpc.ContextServiceStub(grpc_channel)
        
        request = context_pb2.UpdateContextRequest(
            story_id="USR-001",
            task_id="TASK-001",
            role="DEV",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="DECISION",
                    entity_id="DEC-001",
                    payload='{"title":"Use PostgreSQL","rationale":"Better performance"}',
                    reason="Database selection",
                ),
            ],
        )
        
        response = stub.UpdateContext(request)
        
        assert response is not None
        assert response.version > 0
        assert len(response.hash) > 0

    @pytest.mark.skip(reason="Requires running gRPC server")
    def test_rehydrate_session_end_to_end(self, grpc_channel):
        """Test RehydrateSession end-to-end with real server."""
        from services.context.gen import context_pb2, context_pb2_grpc
        
        stub = context_pb2_grpc.ContextServiceStub(grpc_channel)
        
        request = context_pb2.RehydrateSessionRequest(
            case_id="CASE-001",
            roles=["DEV", "QA", "ARCHITECT"],
            include_timeline=True,
            include_summaries=True,
            timeline_events=50,
        )
        
        response = stub.RehydrateSession(request)
        
        assert response is not None
        assert response.case_id == "CASE-001"
        assert len(response.packs) > 0
        assert response.stats.decisions >= 0

    @pytest.mark.skip(reason="Requires running gRPC server")
    def test_validate_scope_end_to_end(self, grpc_channel):
        """Test ValidateScope end-to-end with real server."""
        from services.context.gen import context_pb2, context_pb2_grpc
        
        stub = context_pb2_grpc.ContextServiceStub(grpc_channel)
        
        request = context_pb2.ValidateScopeRequest(
            role="DEV",
            phase="BUILD",
            provided_scopes=["CASE_HEADER", "PLAN_HEADER", "SUBTASKS_ROLE"],
        )
        
        response = stub.ValidateScope(request)
        
        assert response is not None
        assert isinstance(response.allowed, bool)


class TestContextNATSIntegration:
    """Integration tests for NATS messaging."""

    @pytest.mark.asyncio
    async def test_nats_handler_connect(self, mock_nats_client):
        """Test NATS handler connection."""
        from services.context.nats_handler import ContextNATSHandler
        
        with patch('nats.connect', return_value=mock_nats_client):
            handler = ContextNATSHandler(
                nats_url="nats://localhost:4222",
                context_service=Mock(),
            )
            
            await handler.connect()
            
            assert handler.nc is not None
            assert handler.js is not None

    @pytest.mark.asyncio
    async def test_nats_handler_subscribe(self, mock_nats_client):
        """Test NATS handler subscriptions."""
        from services.context.nats_handler import ContextNATSHandler
        
        # Create proper async mock for jetstream
        mock_js = AsyncMock()
        mock_nats_client.jetstream = Mock(return_value=mock_js)
        
        with patch('nats.connect', return_value=mock_nats_client):
            handler = ContextNATSHandler(
                nats_url="nats://localhost:4222",
                context_service=Mock(),
            )
            
            await handler.connect()
            await handler.subscribe()
            
            # Verify subscriptions were created
            assert mock_js.subscribe.call_count == 2

    @pytest.mark.asyncio
    async def test_nats_publish_context_updated(self, mock_nats_client):
        """Test publishing context updated event."""
        from services.context.nats_handler import ContextNATSHandler
        
        # Create proper async mock for jetstream
        mock_js = AsyncMock()
        
        handler = ContextNATSHandler(
            nats_url="nats://localhost:4222",
            context_service=Mock(),
        )
        
        handler.nc = mock_nats_client
        handler.js = mock_js
        
        await handler.publish_context_updated("story-001", 2)
        
        # Verify publish was called
        mock_js.publish.assert_called_once()
        call_args = mock_js.publish.call_args
        
        assert call_args[0][0] == "context.events.updated"
        
        # Verify event data
        event_data = json.loads(call_args[0][1].decode())
        assert event_data["story_id"] == "story-001"
        assert event_data["version"] == 2
        assert event_data["event_type"] == "context.updated"

    @pytest.mark.asyncio
    async def test_nats_handle_update_request(self, mock_nats_client):
        """Test handling update request from NATS."""
        from services.context.nats_handler import ContextNATSHandler
        
        # Create proper async mock for jetstream
        mock_js = AsyncMock()
        
        handler = ContextNATSHandler(
            nats_url="nats://localhost:4222",
            context_service=Mock(),
        )
        
        handler.nc = mock_nats_client
        handler.js = mock_js
        
        # Create mock message
        mock_msg = AsyncMock()
        mock_msg.data = json.dumps({
            "story_id": "story-001",
            "task_id": "task-001",
            "changes": [],
        }).encode()
        
        await handler._handle_update_request(mock_msg)
        
        # Verify message was acknowledged
        mock_msg.ack.assert_called_once()
        
        # Verify response was published
        mock_js.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_nats_handle_rehydrate_request(self, mock_nats_client):
        """Test handling rehydrate request from NATS."""
        from services.context.nats_handler import ContextNATSHandler
        
        # Create proper async mock for jetstream
        mock_js = AsyncMock()
        
        handler = ContextNATSHandler(
            nats_url="nats://localhost:4222",
            context_service=Mock(),
        )
        
        handler.nc = mock_nats_client
        handler.js = mock_js
        
        # Create mock message
        mock_msg = AsyncMock()
        mock_msg.data = json.dumps({
            "case_id": "case-001",
            "roles": ["DEV", "QA"],
        }).encode()
        
        await handler._handle_rehydrate_request(mock_msg)
        
        # Verify message was acknowledged
        mock_msg.ack.assert_called_once()
        
        # Verify response was published
        mock_js.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_nats_error_handling(self, mock_nats_client):
        """Test NATS error handling."""
        from services.context.nats_handler import ContextNATSHandler
        
        handler = ContextNATSHandler(
            nats_url="nats://localhost:4222",
            context_service=Mock(),
        )
        
        handler.nc = mock_nats_client
        handler.js = mock_nats_client.jetstream()
        
        # Create mock message with invalid data
        mock_msg = AsyncMock()
        mock_msg.data = b"invalid json"
        
        await handler._handle_update_request(mock_msg)
        
        # Should NAK the message on error
        mock_msg.nak.assert_called_once()

    @pytest.mark.asyncio
    async def test_nats_close(self, mock_nats_client):
        """Test NATS connection close."""
        from services.context.nats_handler import ContextNATSHandler
        
        handler = ContextNATSHandler(
            nats_url="nats://localhost:4222",
            context_service=Mock(),
        )
        
        handler.nc = mock_nats_client
        
        await handler.close()
        
        mock_nats_client.close.assert_called_once()


class TestContextServiceWithBackends:
    """Integration tests with backend services."""

    @pytest.mark.e2e
    @pytest.mark.skip(reason="Requires Neo4j")
    async def test_context_with_neo4j(self):
        """Test Context Service with real Neo4j."""
        from neo4j import AsyncGraphDatabase
        from services.context.adapters.neo4j_query_store import Neo4jGraphQueryStore
        
        driver = AsyncGraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "password"),
        )
        
        try:
            query_store = Neo4jGraphQueryStore(
                "bolt://localhost:7687",
                "neo4j",
                "password",
            )
            
            # Test basic query
            decisions = query_store.list_decisions("test-case")
            assert isinstance(decisions, list)
            
        finally:
            await driver.close()

    @pytest.mark.e2e
    @pytest.mark.skip(reason="Requires Redis")
    async def test_context_with_redis(self):
        """Test Context Service with real Redis."""
        import redis.asyncio as redis
        from services.context.adapters.redis_planning_read_adapter import (
            RedisPlanningReadAdapter,
        )
        
        redis_client = redis.from_url("redis://localhost:6379")
        
        try:
            adapter = RedisPlanningReadAdapter("localhost", 6379)
            
            # Test basic operation
            _ = adapter.get_case_spec("test-case")
            # Should return None or valid spec
            
        finally:
            await redis_client.close()

    @pytest.mark.e2e
    @pytest.mark.skip(reason="Requires all services")
    async def test_full_workflow(self):
        """Test complete workflow with all services."""
        # 1. Create context via gRPC
        # 2. Verify NATS event published
        # 3. Update context
        # 4. Rehydrate session
        # 5. Verify data in Neo4j
        # 6. Verify data in Redis
        pass


class TestContextServicePerformance:
    """Performance and load tests."""

    @pytest.mark.performance
    @pytest.mark.skip(reason="Performance test")
    def test_get_context_performance(self):
        """Test GetContext performance under load."""
        import time

        
        # Measure response time
        times = []
        for _ in range(100):
            start = time.time()
            # Make request
            end = time.time()
            times.append(end - start)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Assert performance requirements
        assert avg_time < 0.1  # 100ms average
        assert max_time < 0.5  # 500ms max

    @pytest.mark.performance
    @pytest.mark.skip(reason="Performance test")
    def test_concurrent_requests(self):
        """Test handling concurrent requests."""
        import concurrent.futures
        
        def make_request():
            # Make gRPC request
            pass
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            results = [f.result() for f in futures]
        
        # All requests should succeed
        assert len(results) == 100


class TestContextServiceResilience:
    """Resilience and error recovery tests."""

    @pytest.mark.resilience
    def test_neo4j_connection_failure(self):
        """Test behavior when Neo4j is unavailable."""
        from services.context.server import ContextServiceServicer
        
        # Create servicer with invalid Neo4j URI
        with pytest.raises(Exception):  # noqa: B017
            _ = ContextServiceServicer(
                neo4j_uri="bolt://invalid:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
                redis_host="localhost",
                redis_port=6379,
            )

    @pytest.mark.resilience
    def test_redis_connection_failure(self):
        """Test behavior when Redis is unavailable."""
        from services.context.server import ContextServiceServicer
        
        # Create servicer with invalid Redis host
        with pytest.raises(Exception):  # noqa: B017
            _ = ContextServiceServicer(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
                redis_host="invalid",
                redis_port=6379,
            )

    @pytest.mark.resilience
    @pytest.mark.asyncio
    async def test_nats_optional_failure(self):
        """Test that service works without NATS."""
        from services.context.server import ContextServiceServicer
        
        # Create servicer without NATS
        with patch('services.context.server.Neo4jGraphQueryStore'), \
             patch('services.context.server.Neo4jGraphCommandStore'), \
             patch('services.context.server.RedisPlanningReadAdapter'), \
             patch('services.context.server.SessionRehydrationUseCase'), \
             patch('services.context.server.PromptScopePolicy'):
            
            servicer = ContextServiceServicer(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
                redis_host="localhost",
                redis_port=6379,
                nats_handler=None,  # No NATS
            )
            
            # Should work without NATS
            assert servicer.nats_handler is None

    @pytest.mark.resilience
    def test_malformed_request_handling(self):
        """Test handling of malformed requests."""
        from services.context.gen import context_pb2
        from services.context.server import ContextServiceServicer
        
        with patch('services.context.server.Neo4jGraphQueryStore'), \
             patch('services.context.server.Neo4jGraphCommandStore'), \
             patch('services.context.server.RedisPlanningReadAdapter'), \
             patch('services.context.server.SessionRehydrationUseCase'), \
             patch('services.context.server.PromptScopePolicy'):
            
            servicer = ContextServiceServicer(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
                redis_host="localhost",
                redis_port=6379,
            )
            
            # Empty request
            request = context_pb2.GetContextRequest()
            grpc_context = Mock()
            
            # Should handle gracefully
            response = servicer.GetContext(request, grpc_context)
            assert response is not None

