"""Unit tests for PlanningEventsConsumer."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from services.context.consumers.planning_consumer import PlanningEventsConsumer


class TestPlanningEventsConsumer:
    """Unit tests for PlanningEventsConsumer."""
    
    @pytest.fixture
    def mock_nc(self):
        """Mock NATS client."""
        return Mock()
    
    @pytest.fixture
    def mock_js(self):
        """Mock JetStream context."""
        js = Mock()
        js.subscribe = AsyncMock()
        return js
    
    @pytest.fixture
    def mock_cache(self):
        """Mock Redis cache client."""
        cache = Mock()
        cache.scan = Mock(return_value=(0, []))  # Default: no keys
        cache.delete = Mock(return_value=0)
        return cache
    
    @pytest.fixture
    def mock_graph(self):
        """Mock Neo4j graph command store."""
        graph = Mock()
        graph.upsert_entity = Mock()
        return graph
    
    @pytest.fixture
    def consumer(self, mock_nc, mock_js, mock_cache, mock_graph):
        """Create PlanningEventsConsumer instance."""
        return PlanningEventsConsumer(
            nc=mock_nc,
            js=mock_js,
            cache_service=mock_cache,
            graph_command=mock_graph,
        )
    
    @pytest.mark.asyncio
    async def test_start_subscribes_to_events(self, consumer, mock_js):
        """Test that start subscribes to planning events."""
        # Act
        await consumer.start()
        
        # Assert
        assert mock_js.subscribe.call_count == 2
        
        # Verify subscriptions
        calls = mock_js.subscribe.call_args_list
        subjects = [call[1]["subject"] if "subject" in call[1] else call[0][0] for call in calls]
        
        assert "planning.story.transitioned" in subjects
        assert "planning.plan.approved" in subjects
    
    @pytest.mark.asyncio
    async def test_handle_story_transitioned_invalidates_cache(self, consumer, mock_cache):
        """Test that story transition invalidates cache."""
        # Arrange
        event_data = {
            "story_id": "STORY-001",
            "from_phase": "DESIGN",
            "to_phase": "BUILD",
            "timestamp": 1234567890,
        }
        
        # Mock message
        msg = Mock()
        msg.data = json.dumps(event_data).encode()
        msg.ack = AsyncMock()
        msg.nak = AsyncMock()
        
        # Mock cache scan to return some keys
        mock_cache.scan.return_value = (0, [b"context:STORY-001:DEV", b"context:STORY-001:QA"])
        mock_cache.delete.return_value = 2
        
        # Act
        async_mock = AsyncMock(side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        with patch('asyncio.to_thread', new=async_mock):
            await consumer._handle_story_transitioned(msg)
        
        # Assert
        # Should have scanned for keys
        assert mock_cache.scan.called
        scan_call = mock_cache.scan.call_args
        assert "context:STORY-001:*" in str(scan_call)
        
        # Should have deleted keys
        assert mock_cache.delete.called
        
        # Should have acknowledged message
        msg.ack.assert_called_once()
        msg.nak.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_story_transitioned_records_in_graph(self, consumer, mock_graph):
        """Test that story transition is recorded in graph."""
        # Arrange
        event_data = {
            "story_id": "STORY-001",
            "from_phase": "DESIGN",
            "to_phase": "BUILD",
            "timestamp": 1234567890,
        }
        
        msg = Mock()
        msg.data = json.dumps(event_data).encode()
        msg.ack = AsyncMock()
        msg.nak = AsyncMock()
        
        # Act
        async_mock = AsyncMock(side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        with patch('asyncio.to_thread', new=async_mock):
            await consumer._handle_story_transitioned(msg)
        
        # Assert
        # Should have recorded transition in graph
        mock_graph.upsert_entity.assert_called_once()
        
        call_args = mock_graph.upsert_entity.call_args
        # Check kwargs
        assert call_args[1]["entity_type"] == "PhaseTransition"
        assert "STORY-001:1234567890" in call_args[1]["entity_id"]
        
        properties = call_args[1]["properties"]
        assert properties["story_id"] == "STORY-001"
        assert properties["from_phase"] == "DESIGN"
        assert properties["to_phase"] == "BUILD"
    
    @pytest.mark.asyncio
    async def test_handle_story_transitioned_handles_cache_error(self, consumer, mock_cache):
        """Test that cache errors don't break the handler."""
        # Arrange
        event_data = {
            "story_id": "STORY-001",
            "from_phase": "DESIGN",
            "to_phase": "BUILD",
            "timestamp": 1234567890,
        }
        
        msg = Mock()
        msg.data = json.dumps(event_data).encode()
        msg.ack = AsyncMock()
        msg.nak = AsyncMock()
        
        # Mock cache to raise error
        mock_cache.scan.side_effect = Exception("Cache connection error")
        
        # Act
        with patch('asyncio.to_thread', new=AsyncMock(side_effect=Exception("Cache error"))):
            await consumer._handle_story_transitioned(msg)
        
        # Assert
        # Should still acknowledge (cache invalidation is not critical)
        msg.ack.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_story_transitioned_handles_json_error(self, consumer):
        """Test that invalid JSON is handled gracefully."""
        # Arrange
        msg = Mock()
        msg.data = b"invalid json {{"
        msg.ack = AsyncMock()
        msg.nak = AsyncMock()
        
        # Act
        await consumer._handle_story_transitioned(msg)
        
        # Assert
        # Should NAK the message on JSON parse error
        msg.nak.assert_called_once()
        msg.ack.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_plan_approved_records_in_graph(self, consumer, mock_graph):
        """Test that plan approval is recorded in graph."""
        # Arrange
        event_data = {
            "plan_id": "PLAN-001",
            "story_id": "STORY-001",
            "version": 2,
            "approved_by": "architect",
            "timestamp": 1234567890,
        }
        
        msg = Mock()
        msg.data = json.dumps(event_data).encode()
        msg.ack = AsyncMock()
        msg.nak = AsyncMock()
        
        # Act
        async_mock = AsyncMock(side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        with patch('asyncio.to_thread', new=async_mock):
            await consumer._handle_plan_approved(msg)
        
        # Assert
        # Should have recorded approval in graph
        mock_graph.upsert_entity.assert_called_once()
        
        call_args = mock_graph.upsert_entity.call_args
        # Check kwargs
        assert call_args[1]["entity_type"] == "PlanApproval"
        
        properties = call_args[1]["properties"]
        assert properties["plan_id"] == "PLAN-001"
        assert properties["story_id"] == "STORY-001"
        assert properties["approved_by"] == "architect"
        assert properties["timestamp"] == 1234567890
    
    @pytest.mark.asyncio
    async def test_handle_plan_approved_handles_graph_error(self, consumer, mock_graph):
        """Test that graph errors are handled in plan approval."""
        # Arrange
        event_data = {
            "plan_id": "PLAN-001",
            "story_id": "STORY-001",
            "version": 1,
            "approved_by": "architect",
            "timestamp": 1234567890,
        }
        
        msg = Mock()
        msg.data = json.dumps(event_data).encode()
        msg.ack = AsyncMock()
        msg.nak = AsyncMock()
        
        # Mock graph to raise error
        mock_graph.upsert_entity.side_effect = Exception("Graph connection error")
        
        # Act
        with patch('asyncio.to_thread', new=AsyncMock(side_effect=Exception("Graph error"))):
            await consumer._handle_plan_approved(msg)
        
        # Assert
        # Should still acknowledge (logging the error)
        msg.ack.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_consumer(self, consumer):
        """Test that stop logs completion."""
        # Act
        await consumer.stop()
        
        # Assert - should not raise any errors
        # (stop is mainly for logging, no subscriptions to unsubscribe)
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_uses_scan_pattern(self, consumer, mock_cache):
        """Test that cache invalidation uses correct scan pattern."""
        # Arrange
        event_data = {
            "story_id": "STORY-TEST-123",
            "from_phase": "DESIGN",
            "to_phase": "BUILD",
            "timestamp": 1234567890,
        }
        
        msg = Mock()
        msg.data = json.dumps(event_data).encode()
        msg.ack = AsyncMock()
        
        # Mock cache scan
        mock_cache.scan.return_value = (0, [])
        
        # Act
        async_mock = AsyncMock(side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        with patch('asyncio.to_thread', new=async_mock):
            await consumer._handle_story_transitioned(msg)
        
        # Assert
        # Verify scan was called with correct pattern
        mock_cache.scan.assert_called()
        call_kwargs = mock_cache.scan.call_args[1]
        assert call_kwargs["match"] == "context:STORY-TEST-123:*"
    
    @pytest.mark.asyncio
    async def test_multiple_cache_keys_deleted(self, consumer, mock_cache):
        """Test that multiple cache keys are deleted in batches."""
        # Arrange
        event_data = {
            "story_id": "STORY-001",
            "from_phase": "BUILD",
            "to_phase": "TEST",
            "timestamp": 1234567890,
        }
        
        msg = Mock()
        msg.data = json.dumps(event_data).encode()
        msg.ack = AsyncMock()
        
        # Mock multiple keys in cache
        keys = [
            b"context:STORY-001:DEV",
            b"context:STORY-001:QA",
            b"context:STORY-001:ARCHITECT",
        ]
        mock_cache.scan.return_value = (0, keys)
        mock_cache.delete.return_value = 3
        
        # Act
        async_mock = AsyncMock(side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        with patch('asyncio.to_thread', new=async_mock):
            await consumer._handle_story_transitioned(msg)
        
        # Assert
        # Should have deleted all keys
        mock_cache.delete.assert_called_once()
        delete_args = mock_cache.delete.call_args[0]
        assert len(delete_args) == 3

