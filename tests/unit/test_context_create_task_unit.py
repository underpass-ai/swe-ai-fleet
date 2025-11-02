"""
Unit tests for Context Service CreateTask method.
Tests the CreateTask gRPC API without touching real infrastructure.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestCreateTask:
    """Unit tests for CreateTask gRPC method."""

    @pytest.fixture
    def mock_graph_command(self):
        """Mock Neo4j command store."""
        mock = Mock()
        mock.upsert_entity = Mock()
        mock.relate = Mock()
        return mock

    @pytest.fixture
    def mock_planning_read(self):
        """Mock Redis planning read adapter."""
        mock = Mock()
        mock_client = Mock()
        mock_client.hset = Mock()
        mock.client = mock_client
        return mock

    @pytest.fixture
    def context_servicer(self, mock_graph_command, mock_planning_read):
        """Create Context Service servicer with mocked dependencies."""
        from services.context.server import ContextServiceServicer

        # Patch ContextServiceServicer to avoid full initialization
        servicer = Mock(spec=ContextServiceServicer)
        servicer.graph_command = mock_graph_command
        servicer.planning_read = mock_planning_read

        # Import actual CreateTask method
        from services.context import server

        # Bind the actual method to our mock servicer
        servicer.CreateTask = server.ContextServiceServicer.CreateTask.__get__(servicer)

        return servicer

    @pytest.mark.asyncio
    async def test_create_task_success(self, context_servicer, mock_graph_command, mock_planning_read):
        """Test successful task creation with all fields."""
        from services.context.gen import context_pb2

        # Arrange
        request = context_pb2.CreateTaskRequest(
            story_id="US-123",
            task_id="TASK-001",
            title="Implement authentication service",
            description="Create JWT-based authentication with refresh tokens",
            role="DEV",
            dependencies=["TASK-000"],
            priority=1,
            estimated_hours=8
        )

        grpc_context = Mock()

        # Act
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            # Configure to_thread to directly call the function
            async def execute_sync(func, *args, **kwargs):
                return func(*args, **kwargs)

            mock_to_thread.side_effect = execute_sync

            response = await context_servicer.CreateTask(request, grpc_context)

        # Assert - Response
        assert response.task_id == "TASK-001"
        assert response.story_id == "US-123"
        assert response.status == "PENDING"

        # Assert - Neo4j upsert_entity called correctly
        assert mock_graph_command.upsert_entity.called
        upsert_call = mock_graph_command.upsert_entity.call_args
        assert upsert_call[0][0] == "Task"  # label
        assert upsert_call[0][1] == "TASK-001"  # id
        task_props = upsert_call[0][2]  # properties
        assert task_props["task_id"] == "TASK-001"
        assert task_props["story_id"] == "US-123"
        assert task_props["title"] == "Implement authentication service"
        assert task_props["role"] == "DEV"
        assert task_props["priority"] == 1
        assert task_props["estimated_hours"] == 8
        assert task_props["status"] == "PENDING"
        assert "created_at" in task_props
        assert "updated_at" in task_props

        # Assert - Neo4j relate called for BELONGS_TO relationship
        relate_calls = mock_graph_command.relate.call_args_list
        assert len(relate_calls) == 2  # BELONGS_TO + DEPENDS_ON

        belongs_to_call = relate_calls[0]
        assert belongs_to_call[1]["src_id"] == "TASK-001"
        assert belongs_to_call[1]["rel_type"] == "BELONGS_TO"
        assert belongs_to_call[1]["dst_id"] == "US-123"
        assert belongs_to_call[1]["src_labels"] == ["Task"]
        assert belongs_to_call[1]["dst_labels"] == ["ProjectCase"]

        # Assert - Neo4j relate called for DEPENDS_ON relationship
        depends_on_call = relate_calls[1]
        assert depends_on_call[1]["src_id"] == "TASK-001"
        assert depends_on_call[1]["rel_type"] == "DEPENDS_ON"
        assert depends_on_call[1]["dst_id"] == "TASK-000"
        assert depends_on_call[1]["src_labels"] == ["Task"]
        assert depends_on_call[1]["dst_labels"] == ["Task"]

        # Assert - Valkey hset called correctly
        assert mock_planning_read.client.hset.called
        hset_call = mock_planning_read.client.hset.call_args
        assert hset_call[0][0] == "task:TASK-001"  # key
        task_data = hset_call[1]["mapping"]
        assert task_data["task_id"] == "TASK-001"
        assert task_data["story_id"] == "US-123"
        assert task_data["role"] == "DEV"
        assert task_data["dependencies"] == "TASK-000"
        assert task_data["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_create_task_no_dependencies(
        self, context_servicer, mock_graph_command, mock_planning_read
    ):
        """Test task creation without dependencies."""
        from services.context.gen import context_pb2

        # Arrange
        request = context_pb2.CreateTaskRequest(
            story_id="US-456",
            task_id="TASK-100",
            title="Setup database schema",
            description="Initialize PostgreSQL schema for user management",
            role="DEV",
            dependencies=[],  # No dependencies
            priority=2,
            estimated_hours=4
        )

        grpc_context = Mock()

        # Act
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            async def execute_sync(func, *args, **kwargs):
                return func(*args, **kwargs)

            mock_to_thread.side_effect = execute_sync

            response = await context_servicer.CreateTask(request, grpc_context)

        # Assert
        assert response.task_id == "TASK-100"
        assert response.story_id == "US-456"

        # Should have only 1 relate call (BELONGS_TO, no DEPENDS_ON)
        relate_calls = mock_graph_command.relate.call_args_list
        assert len(relate_calls) == 1

        # Valkey should have empty dependencies string
        hset_call = mock_planning_read.client.hset.call_args
        task_data = hset_call[1]["mapping"]
        assert task_data["dependencies"] == ""

    @pytest.mark.asyncio
    async def test_create_task_multiple_dependencies(
        self, context_servicer, mock_graph_command, mock_planning_read
    ):
        """Test task creation with multiple dependencies."""
        from services.context.gen import context_pb2

        # Arrange
        request = context_pb2.CreateTaskRequest(
            story_id="US-789",
            task_id="TASK-200",
            title="Implement user login",
            description="Build login endpoint after auth service is ready",
            role="DEV",
            dependencies=["TASK-100", "TASK-150", "TASK-175"],
            priority=1,
            estimated_hours=6
        )

        grpc_context = Mock()

        # Act
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            async def execute_sync(func, *args, **kwargs):
                return func(*args, **kwargs)

            mock_to_thread.side_effect = execute_sync

            response = await context_servicer.CreateTask(request, grpc_context)

        # Assert
        assert response.task_id == "TASK-200"

        # Should have 4 relate calls (1 BELONGS_TO + 3 DEPENDS_ON)
        relate_calls = mock_graph_command.relate.call_args_list
        assert len(relate_calls) == 4

        # Verify BELONGS_TO is first
        assert relate_calls[0][1]["rel_type"] == "BELONGS_TO"

        # Verify all 3 DEPENDS_ON relationships
        depends_on_rels = [call[1] for call in relate_calls[1:]]
        assert all(rel["rel_type"] == "DEPENDS_ON" for rel in depends_on_rels)
        assert all(rel["src_id"] == "TASK-200" for rel in depends_on_rels)

        dep_ids = {rel["dst_id"] for rel in depends_on_rels}
        assert dep_ids == {"TASK-100", "TASK-150", "TASK-175"}

        # Valkey should have comma-separated dependencies
        hset_call = mock_planning_read.client.hset.call_args
        task_data = hset_call[1]["mapping"]
        assert task_data["dependencies"] == "TASK-100,TASK-150,TASK-175"

    @pytest.mark.asyncio
    async def test_create_task_neo4j_failure(
        self, context_servicer, mock_graph_command, mock_planning_read
    ):
        """Test CreateTask handles Neo4j failures gracefully."""
        from services.context.gen import context_pb2

        # Arrange
        request = context_pb2.CreateTaskRequest(
            story_id="US-ERROR",
            task_id="TASK-ERROR",
            title="Test task",
            description="Test description",
            role="DEV",
            dependencies=[],
            priority=1,
            estimated_hours=2
        )

        grpc_context = Mock()

        # Configure Neo4j to raise exception
        mock_graph_command.upsert_entity.side_effect = RuntimeError("Neo4j connection failed")

        # Act
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            async def execute_sync(func, *args, **kwargs):
                return func(*args, **kwargs)

            mock_to_thread.side_effect = execute_sync

            response = await context_servicer.CreateTask(request, grpc_context)

        # Assert - Should return empty response
        assert response.task_id == ""
        assert response.story_id == ""

        # Assert - gRPC context should have error set
        grpc_context.set_code.assert_called()
        grpc_context.set_details.assert_called()

    @pytest.mark.asyncio
    async def test_create_task_valkey_failure(
        self, context_servicer, mock_graph_command, mock_planning_read
    ):
        """Test CreateTask handles Valkey failures gracefully."""
        from services.context.gen import context_pb2

        # Arrange
        request = context_pb2.CreateTaskRequest(
            story_id="US-VALKEY-ERROR",
            task_id="TASK-VALKEY-ERROR",
            title="Test task",
            description="Test description",
            role="QA",
            dependencies=[],
            priority=3,
            estimated_hours=1
        )

        grpc_context = Mock()

        # Neo4j works but Valkey fails
        mock_planning_read.client.hset.side_effect = RuntimeError("Valkey connection timeout")

        # Act
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            async def execute_sync(func, *args, **kwargs):
                return func(*args, **kwargs)

            mock_to_thread.side_effect = execute_sync

            response = await context_servicer.CreateTask(request, grpc_context)

        # Assert - Should return empty response
        assert response.task_id == ""

        # Assert - Error should be logged and returned
        grpc_context.set_code.assert_called()
        grpc_context.set_details.assert_called()

