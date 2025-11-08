"""
Unit tests for Context Service CreateStory method.
Tests the CreateStory gRPC API without touching real infrastructure.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestCreateStory:
    """Unit tests for CreateStory gRPC method."""

    @pytest.fixture
    def mock_graph_command(self):
        """Mock Neo4j command store."""
        mock = Mock()
        mock.upsert_entity = Mock()
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

        # Patch to avoid full initialization
        servicer = Mock(spec=ContextServiceServicer)
        servicer.graph_command = mock_graph_command
        servicer.planning_read = mock_planning_read

        # Import actual CreateStory method
        from services.context import server

        # Bind the actual method to our mock servicer
        servicer.CreateStory = server.ContextServiceServicer.CreateStory.__get__(servicer)

        return servicer

    @pytest.mark.asyncio
    async def test_create_story_success_with_default_phase(
        self, context_servicer, mock_graph_command, mock_planning_read
    ):
        """Test successful story creation with default DESIGN phase."""
        from services.context.gen import context_pb2

        # Arrange
        request = context_pb2.CreateStoryRequest(
            story_id="US-001",
            title="Implement OAuth2 authentication",
            description="Add Google and GitHub login support",
            initial_phase=""  # Empty = default to DESIGN
        )

        grpc_context = Mock()

        # Act
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            async def execute_sync(func, *args, **kwargs):
                return func(*args, **kwargs)

            mock_to_thread.side_effect = execute_sync

            response = await context_servicer.CreateStory(request, grpc_context)

        # Assert - Response
        assert response.story_id == "US-001"
        assert response.current_phase == "DESIGN"  # Default phase
        assert response.context_id == "ctx-US-001"

        # Assert - Neo4j upsert_entity called correctly
        assert mock_graph_command.upsert_entity.called
        upsert_call = mock_graph_command.upsert_entity.call_args
        assert upsert_call[0][0] == "ProjectCase"  # label
        assert upsert_call[0][1] == "US-001"  # id
        story_props = upsert_call[0][2]  # properties
        assert story_props["story_id"] == "US-001"
        assert story_props["title"] == "Implement OAuth2 authentication"
        assert story_props["description"] == "Add Google and GitHub login support"
        assert story_props["current_phase"] == "DESIGN"
        assert story_props["status"] == "ACTIVE"
        assert "created_at" in story_props
        assert "updated_at" in story_props

        # Assert - Valkey hset called correctly
        assert mock_planning_read.client.hset.called
        hset_call = mock_planning_read.client.hset.call_args
        assert hset_call[0][0] == "story:US-001"  # key
        story_data = hset_call[1]["mapping"]
        assert story_data["story_id"] == "US-001"
        assert story_data["title"] == "Implement OAuth2 authentication"
        assert story_data["current_phase"] == "DESIGN"
        assert story_data["status"] == "ACTIVE"

    @pytest.mark.asyncio
    async def test_create_story_success_with_custom_phase(
        self, context_servicer, mock_graph_command, mock_planning_read
    ):
        """Test successful story creation with custom BUILD phase."""
        from services.context.gen import context_pb2

        # Arrange
        request = context_pb2.CreateStoryRequest(
            story_id="US-002",
            title="Add GraphQL API",
            description="Replace REST with GraphQL",
            initial_phase="BUILD"  # Custom phase
        )

        grpc_context = Mock()

        # Act
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            async def execute_sync(func, *args, **kwargs):
                return func(*args, **kwargs)

            mock_to_thread.side_effect = execute_sync

            response = await context_servicer.CreateStory(request, grpc_context)

        # Assert
        assert response.story_id == "US-002"
        assert response.current_phase == "BUILD"  # Custom phase respected

        # Verify Neo4j properties
        upsert_call = mock_graph_command.upsert_entity.call_args
        story_props = upsert_call[0][2]
        assert story_props["current_phase"] == "BUILD"

        # Verify Valkey properties
        hset_call = mock_planning_read.client.hset.call_args
        story_data = hset_call[1]["mapping"]
        assert story_data["current_phase"] == "BUILD"

    @pytest.mark.asyncio
    async def test_create_story_neo4j_failure(
        self, context_servicer, mock_graph_command, mock_planning_read
    ):
        """Test CreateStory handles Neo4j failures gracefully."""
        from services.context.gen import context_pb2

        # Arrange
        request = context_pb2.CreateStoryRequest(
            story_id="US-ERROR",
            title="Error test",
            description="This should fail",
            initial_phase="DESIGN"
        )

        grpc_context = Mock()

        # Configure Neo4j to raise exception
        mock_graph_command.upsert_entity.side_effect = RuntimeError("Neo4j connection timeout")

        # Act
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            async def execute_sync(func, *args, **kwargs):
                return func(*args, **kwargs)

            mock_to_thread.side_effect = execute_sync

            response = await context_servicer.CreateStory(request, grpc_context)

        # Assert - Should return empty response
        assert response.story_id == ""
        assert response.context_id == ""
        assert response.current_phase == ""

        # Assert - gRPC context should have error set
        grpc_context.set_code.assert_called_once()
        grpc_context.set_details.assert_called_once()

        # Verify error code is INTERNAL
        import grpc
        call_args = grpc_context.set_code.call_args
        assert call_args[0][0] == grpc.StatusCode.INTERNAL

        # Verify error details contain exception message
        details_call = grpc_context.set_details.call_args
        assert "Neo4j connection timeout" in str(details_call[0][0])

    @pytest.mark.asyncio
    async def test_create_story_valkey_failure(
        self, context_servicer, mock_graph_command, mock_planning_read
    ):
        """Test CreateStory handles Valkey failures gracefully."""
        from services.context.gen import context_pb2

        # Arrange
        request = context_pb2.CreateStoryRequest(
            story_id="US-VALKEY-ERROR",
            title="Valkey error test",
            description="Redis should fail",
            initial_phase="DESIGN"
        )

        grpc_context = Mock()

        # Neo4j works but Valkey fails
        mock_planning_read.client.hset.side_effect = RuntimeError("Valkey connection lost")

        # Act
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            async def execute_sync(func, *args, **kwargs):
                return func(*args, **kwargs)

            mock_to_thread.side_effect = execute_sync

            response = await context_servicer.CreateStory(request, grpc_context)

        # Assert - Should return empty response
        assert response.story_id == ""

        # Assert - Error should be logged and returned
        grpc_context.set_code.assert_called_once()
        grpc_context.set_details.assert_called_once()

        # Verify error message
        details_call = grpc_context.set_details.call_args
        assert "Valkey connection lost" in str(details_call[0][0])

    @pytest.mark.asyncio
    async def test_create_story_with_special_characters(
        self, context_servicer, mock_graph_command, mock_planning_read
    ):
        """Test CreateStory handles special characters in title/description."""
        from services.context.gen import context_pb2

        # Arrange
        request = context_pb2.CreateStoryRequest(
            story_id="US-003",
            title="Test with 'quotes' and \"double quotes\"",
            description="Description with\nnewlines\nand\ttabs and émojis 🚀",
            initial_phase="TEST"
        )

        grpc_context = Mock()

        # Act
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            async def execute_sync(func, *args, **kwargs):
                return func(*args, **kwargs)

            mock_to_thread.side_effect = execute_sync

            response = await context_servicer.CreateStory(request, grpc_context)

        # Assert
        assert response.story_id == "US-003"

        # Verify special characters are preserved in Neo4j
        upsert_call = mock_graph_command.upsert_entity.call_args
        story_props = upsert_call[0][2]
        assert "quotes" in story_props["title"]
        assert "🚀" in story_props["description"]
        assert "\n" in story_props["description"]

        # Verify special characters are preserved in Valkey
        hset_call = mock_planning_read.client.hset.call_args
        story_data = hset_call[1]["mapping"]
        assert "quotes" in story_data["title"]
        assert "🚀" in story_data["description"]

    @pytest.mark.asyncio
    async def test_create_story_dual_persistence(
        self, context_servicer, mock_graph_command, mock_planning_read
    ):
        """Test CreateStory persists to both Neo4j AND Valkey."""
        from services.context.gen import context_pb2

        # Arrange
        request = context_pb2.CreateStoryRequest(
            story_id="US-DUAL",
            title="Dual persistence test",
            description="Should save to both databases",
            initial_phase="DESIGN"
        )

        grpc_context = Mock()

        # Act
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            call_count = 0

            async def execute_sync(func, *args, **kwargs):
                nonlocal call_count
                call_count += 1
                return func(*args, **kwargs)

            mock_to_thread.side_effect = execute_sync

            response = await context_servicer.CreateStory(request, grpc_context)

        # Assert - Both databases were called
        assert call_count == 2  # One for Neo4j, one for Valkey

        # Assert - Neo4j upsert was called
        assert mock_graph_command.upsert_entity.called
        neo4j_call = mock_graph_command.upsert_entity.call_args
        assert neo4j_call[0][0] == "ProjectCase"
        assert neo4j_call[0][1] == "US-DUAL"

        # Assert - Valkey hset was called
        assert mock_planning_read.client.hset.called
        valkey_call = mock_planning_read.client.hset.call_args
        assert valkey_call[0][0] == "story:US-DUAL"

        # Assert - Both have same data
        neo4j_props = neo4j_call[0][2]
        valkey_data = valkey_call[1]["mapping"]

        assert neo4j_props["story_id"] == valkey_data["story_id"]
        assert neo4j_props["title"] == valkey_data["title"]
        assert neo4j_props["description"] == valkey_data["description"]
        assert neo4j_props["current_phase"] == valkey_data["current_phase"]
        assert neo4j_props["status"] == valkey_data["status"]
        assert neo4j_props["created_at"] == valkey_data["created_at"]

    @pytest.mark.asyncio
    async def test_create_story_timestamps_are_iso_format(
        self, context_servicer, mock_graph_command, mock_planning_read
    ):
        """Test CreateStory uses ISO 8601 timestamp format."""
        from services.context.gen import context_pb2

        # Arrange
        request = context_pb2.CreateStoryRequest(
            story_id="US-TIME",
            title="Timestamp test",
            description="Verify ISO 8601 format",
            initial_phase="DESIGN"
        )

        grpc_context = Mock()

        # Act
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            async def execute_sync(func, *args, **kwargs):
                return func(*args, **kwargs)

            mock_to_thread.side_effect = execute_sync

            response = await context_servicer.CreateStory(request, grpc_context)

        # Assert - Check timestamp format in Neo4j
        upsert_call = mock_graph_command.upsert_entity.call_args
        story_props = upsert_call[0][2]

        # Verify ISO 8601 format (YYYY-MM-DDTHH:MM:SS.ffffff+00:00)
        import re
        iso_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+00:00'

        assert re.match(iso_pattern, story_props["created_at"])
        assert re.match(iso_pattern, story_props["updated_at"])

        # created_at and updated_at should be the same on creation
        assert story_props["created_at"] == story_props["updated_at"]

