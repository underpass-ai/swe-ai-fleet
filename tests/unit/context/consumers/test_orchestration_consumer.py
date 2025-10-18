"""Unit tests for OrchestrationEventsConsumer."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from services.context.consumers.orchestration_consumer import OrchestrationEventsConsumer


class TestOrchestrationEventsConsumer:
    """Unit tests for OrchestrationEventsConsumer."""
    
    @pytest.fixture
    def mock_nc(self):
        """Mock NATS client."""
        return Mock()
    
    @pytest.fixture
    def mock_js(self):
        """Mock JetStream context."""
        js = Mock()
        js.subscribe = AsyncMock()
        js.pull_subscribe = AsyncMock(return_value=Mock())  # Return mock subscription
        return js
    
    @pytest.fixture
    def mock_graph(self):
        """Mock Neo4j graph command store."""
        graph = Mock()
        graph.upsert_entity = Mock()
        return graph
    
    @pytest.fixture
    def mock_publisher(self):
        """Mock NATS publisher."""
        publisher = Mock()
        publisher.publish_context_updated = AsyncMock()
        return publisher
    
    @pytest.fixture
    def mock_project_decision(self):
        """Mock ProjectDecisionUseCase."""
        use_case = Mock()
        use_case.execute = Mock()
        return use_case
    
    @pytest.fixture
    def mock_update_subtask(self):
        """Mock UpdateSubtaskStatusUseCase."""
        use_case = Mock()
        use_case.execute = Mock()
        return use_case
    
    @pytest.fixture
    def consumer(self, mock_nc, mock_js, mock_graph, mock_publisher):
        """Create OrchestrationEventsConsumer instance with mocked use cases."""
        with patch('services.context.consumers.orchestration_consumer.ProjectDecisionUseCase'):
            with patch('services.context.consumers.orchestration_consumer.UpdateSubtaskStatusUseCase'):
                consumer = OrchestrationEventsConsumer(
                    nc=mock_nc,
                    js=mock_js,
                    graph_command=mock_graph,
                    nats_publisher=mock_publisher,
                )
                # Replace with mocks that have proper execute methods
                consumer.project_decision = Mock()
                consumer.project_decision.execute = Mock()
                consumer.update_subtask_status = Mock()
                consumer.update_subtask_status.execute = Mock()
                return consumer
    
    @pytest.mark.asyncio
    async def test_start_subscribes_to_events(self, consumer, mock_js):
        """Test that start subscribes to orchestration events."""
        # Act
        await consumer.start()
        
        # Assert - should use pull_subscribe for durable consumers
        assert mock_js.pull_subscribe.call_count == 2
        
        # Verify subscriptions
        calls = mock_js.pull_subscribe.call_args_list
        subjects = [call[1]["subject"] if "subject" in call[1] else call[0][0] for call in calls]
        
        assert "orchestration.deliberation.completed" in subjects
        assert "orchestration.task.dispatched" in subjects
    
    @pytest.mark.asyncio
    async def test_handle_deliberation_completed_with_decisions(self, consumer):
        """Test handling deliberation completed event with decisions."""
        # Arrange
        event_data = {
            "story_id": "STORY-001",
            "task_id": "TASK-001",
            "decisions": [
                {
                    "id": "DEC-001",
                    "type": "TECHNICAL",
                    "rationale": "Use Redis for caching",
                },
                {
                    "id": "DEC-002",
                    "type": "ARCHITECTURAL",
                    "rationale": "Implement event sourcing",
                    "affected_subtask": "SUBTASK-001",
                }
            ],
            "execution_id": "exec-123",
        }
        
        msg = Mock()
        msg.data = json.dumps(event_data).encode()
        msg.ack = AsyncMock()
        msg.nak = AsyncMock()
        
        # Act
        async_mock = AsyncMock(side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        with patch('asyncio.to_thread', new=async_mock):
            await consumer._handle_deliberation_completed(msg)
        
        # Assert
        # Should have called project_decision use case for each decision
        assert consumer.project_decision.execute.call_count == 2
        
        # Verify first decision
        first_call = consumer.project_decision.execute.call_args_list[0]
        payload = first_call[0][0]
        assert payload["node_id"] == "DEC-001"
        assert payload["kind"] == "TECHNICAL"
        
        # Should have acknowledged
        msg.ack.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_deliberation_completed_publishes_context_updated(
        self, consumer, mock_publisher
    ):
        """Test that deliberation completed triggers context.updated event."""
        # Arrange
        event_data = {
            "story_id": "STORY-001",
            "task_id": "TASK-001",
            "decisions": [],
            "execution_id": "exec-123",
        }
        
        msg = Mock()
        msg.data = json.dumps(event_data).encode()
        msg.ack = AsyncMock()
        
        # Act
        await consumer._handle_deliberation_completed(msg)
        
        # Assert
        # Should have published context.updated
        mock_publisher.publish_context_updated.assert_called_once()
        call_args = mock_publisher.publish_context_updated.call_args
        assert call_args[1]["story_id"] == "STORY-001"
    
    @pytest.mark.asyncio
    async def test_handle_deliberation_completed_handles_use_case_error(self, consumer):
        """Test that use case errors don't break the handler."""
        # Arrange
        event_data = {
            "story_id": "STORY-001",
            "task_id": "TASK-001",
            "decisions": [
                {
                    "id": "DEC-001",
                    "type": "TECHNICAL",
                    "rationale": "Test decision",
                }
            ],
            "execution_id": "exec-123",
        }
        
        msg = Mock()
        msg.data = json.dumps(event_data).encode()
        msg.ack = AsyncMock()
        
        # Mock asyncio.to_thread to raise error
        async def raise_error(f, *args, **kwargs):
            raise RuntimeError("Use case error")
        
        # Act
        with patch('asyncio.to_thread', new=raise_error):
            await consumer._handle_deliberation_completed(msg)
        
        # Assert
        # Should still acknowledge (individual decision errors are logged)
        msg.ack.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_deliberation_completed_with_empty_decisions(self, consumer):
        """Test handling deliberation with no decisions."""
        # Arrange
        event_data = {
            "story_id": "STORY-001",
            "task_id": "TASK-001",
            "decisions": [],  # No decisions
            "execution_id": "exec-123",
        }
        
        msg = Mock()
        msg.data = json.dumps(event_data).encode()
        msg.ack = AsyncMock()
        
        # Act
        await consumer._handle_deliberation_completed(msg)
        
        # Assert
        # Should not call use case if no decisions
        consumer.project_decision.execute.assert_not_called()
        
        # Should still acknowledge
        msg.ack.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_task_dispatched_updates_subtask_status(self, consumer):
        """Test that task dispatch updates subtask status."""
        # Arrange
        event_data = {
            "story_id": "STORY-001",
            "task_id": "TASK-001",
            "agent_id": "agent-dev-001",
            "role": "DEV",
            "timestamp": 1234567890,
        }
        
        msg = Mock()
        msg.data = json.dumps(event_data).encode()
        msg.ack = AsyncMock()
        msg.nak = AsyncMock()
        
        # Act
        async_mock = AsyncMock(side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        with patch('asyncio.to_thread', new=async_mock):
            await consumer._handle_task_dispatched(msg)
        
        # Assert
        # Should have called update_subtask_status use case
        consumer.update_subtask_status.execute.assert_called_once()
        
        payload = consumer.update_subtask_status.execute.call_args[0][0]
        assert payload["sub_id"] == "TASK-001"
        assert payload["status"] == "IN_PROGRESS"
        
        msg.ack.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_task_dispatched_records_dispatch_event(self, consumer, mock_graph):
        """Test that task dispatch is recorded in graph."""
        # Arrange
        event_data = {
            "story_id": "STORY-001",
            "task_id": "TASK-001",
            "agent_id": "agent-dev-001",
            "role": "DEV",
            "timestamp": 1234567890,
        }
        
        msg = Mock()
        msg.data = json.dumps(event_data).encode()
        msg.ack = AsyncMock()
        
        # Act
        async_mock = AsyncMock(side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        with patch('asyncio.to_thread', new=async_mock):
            await consumer._handle_task_dispatched(msg)
        
        # Assert
        # Should have recorded dispatch event (called twice: once by use case, once by handler)
        assert mock_graph.upsert_entity.call_count >= 1
        
        # Find the TaskDispatch call
        task_dispatch_call = None
        for call in mock_graph.upsert_entity.call_args_list:
            if call[1].get("label") == "TaskDispatch":
                task_dispatch_call = call
                break
        
        assert task_dispatch_call is not None
        properties = task_dispatch_call[1]["properties"]
        assert properties["task_id"] == "TASK-001"
        assert properties["agent_id"] == "agent-dev-001"
        assert properties["role"] == "DEV"
        assert properties["status"] == "dispatched"
    
    @pytest.mark.asyncio
    async def test_handle_task_dispatched_handles_use_case_error(self, consumer):
        """Test that use case errors in task dispatch are handled."""
        # Arrange
        event_data = {
            "story_id": "STORY-001",
            "task_id": "TASK-001",
            "agent_id": "agent-001",
            "role": "DEV",
            "timestamp": 1234567890,
        }
        
        msg = Mock()
        msg.data = json.dumps(event_data).encode()
        msg.ack = AsyncMock()
        
        # Mock asyncio.to_thread to raise error
        async def raise_error(f, *args, **kwargs):
            raise RuntimeError("Use case error")
        
        # Act
        with patch('asyncio.to_thread', new=raise_error):
            await consumer._handle_task_dispatched(msg)
        
        # Assert
        # Should still acknowledge (error is logged)
        msg.ack.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_task_dispatched_handles_json_error(self, consumer):
        """Test that invalid JSON in task dispatch is handled."""
        # Arrange
        msg = Mock()
        msg.data = b"invalid json {{"
        msg.ack = AsyncMock()
        msg.nak = AsyncMock()
        
        # Act
        await consumer._handle_task_dispatched(msg)
        
        # Assert
        # Should NAK on JSON error
        msg.nak.assert_called_once()
        msg.ack.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_stop_consumer(self, consumer):
        """Test that stop logs completion."""
        # Act
        await consumer.stop()
        
        # Assert - should not raise errors
    
    @pytest.mark.asyncio
    async def test_decision_with_affected_subtask(self, consumer):
        """Test that decision with affected_subtask includes sub_id."""
        # Arrange
        event_data = {
            "story_id": "STORY-001",
            "task_id": "TASK-001",
            "decisions": [
                {
                    "id": "DEC-001",
                    "type": "TECHNICAL",
                    "rationale": "Decision affecting subtask",
                    "affected_subtask": "SUBTASK-123",
                }
            ],
            "execution_id": "exec-123",
        }
        
        msg = Mock()
        msg.data = json.dumps(event_data).encode()
        msg.ack = AsyncMock()
        
        # Act
        async_mock = AsyncMock(side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        with patch('asyncio.to_thread', new=async_mock):
            await consumer._handle_deliberation_completed(msg)
        
        # Assert
        call_args = consumer.project_decision.execute.call_args
        payload = call_args[0][0]
        assert payload["sub_id"] == "SUBTASK-123"

