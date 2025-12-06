"""Tests for ContextGrpcMapper."""

from unittest.mock import MagicMock

import pytest
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.infrastructure.mappers.context_grpc_mapper import ContextGrpcMapper


class TestContextGrpcMapperToGetContextRequest:
    """Test conversion from domain objects to GetContextRequest proto."""

    def test_to_get_context_request_success(self) -> None:
        """Test successful conversion to proto message."""
        story_id = StoryId("story-001")
        role = "developer"
        phase = "plan"

        # Mock context_pb2 module
        mock_context_pb2 = MagicMock()
        mock_request = MagicMock()
        mock_context_pb2.GetContextRequest = MagicMock(return_value=mock_request)

        # Patch the mapper's context_pb2
        import planning.infrastructure.mappers.context_grpc_mapper as mapper_module
        original_pb2 = mapper_module.context_pb2
        mapper_module.context_pb2 = mock_context_pb2

        try:
            # Call mapper - we only verify the protobuf constructor was called correctly
            ContextGrpcMapper.to_get_context_request(
                story_id=story_id,
                role=role,
                phase=phase,
            )

            # Verify GetContextRequest was called with correct parameters
            mock_context_pb2.GetContextRequest.assert_called_once_with(
                story_id="story-001",
                role="developer",
                phase="PLAN",
            )
        finally:
            # Restore original
            mapper_module.context_pb2 = original_pb2

    def test_to_get_context_request_phase_uppercase(self) -> None:
        """Test that phase is converted to uppercase."""
        story_id = StoryId("story-001")
        role = "developer"
        phase = "build"

        mock_context_pb2 = MagicMock()
        mock_request = MagicMock()
        mock_context_pb2.GetContextRequest = MagicMock(return_value=mock_request)

        import planning.infrastructure.mappers.context_grpc_mapper as mapper_module
        original_pb2 = mapper_module.context_pb2
        mapper_module.context_pb2 = mock_context_pb2

        try:
            # Call mapper - we only verify the protobuf constructor was called correctly
            ContextGrpcMapper.to_get_context_request(
                story_id=story_id,
                role=role,
                phase=phase,
            )

            mock_context_pb2.GetContextRequest.assert_called_once_with(
                story_id="story-001",
                role="developer",
                phase="BUILD",
            )
        finally:
            mapper_module.context_pb2 = original_pb2

    def test_to_get_context_request_rejects_empty_story_id(self) -> None:
        """Test that mapper rejects empty story_id."""
        role = "developer"
        phase = "plan"

        # StoryId validates and raises before mapper can check
        with pytest.raises(ValueError, match="StoryId cannot be empty"):
            ContextGrpcMapper.to_get_context_request(
                story_id=StoryId(""),  # type: ignore
                role=role,
                phase=phase,
            )

    def test_to_get_context_request_rejects_empty_role(self) -> None:
        """Test that mapper rejects empty role."""
        story_id = StoryId("story-001")
        phase = "plan"

        with pytest.raises(ValueError, match="role cannot be empty"):
            ContextGrpcMapper.to_get_context_request(
                story_id=story_id,
                role="",
                phase=phase,
            )

    def test_to_get_context_request_rejects_empty_phase(self) -> None:
        """Test that mapper rejects empty phase."""
        story_id = StoryId("story-001")
        role = "developer"

        with pytest.raises(ValueError, match="phase cannot be empty"):
            ContextGrpcMapper.to_get_context_request(
                story_id=story_id,
                role=role,
                phase="",
            )

    def test_to_get_context_request_handles_whitespace(self) -> None:
        """Test that role whitespace is stripped."""
        story_id = StoryId("story-001")
        role = "  developer  "
        phase = "plan"

        mock_context_pb2 = MagicMock()
        mock_request = MagicMock()
        mock_context_pb2.GetContextRequest = MagicMock(return_value=mock_request)

        import planning.infrastructure.mappers.context_grpc_mapper as mapper_module
        original_pb2 = mapper_module.context_pb2
        mapper_module.context_pb2 = mock_context_pb2

        try:
            ContextGrpcMapper.to_get_context_request(
                story_id=story_id,
                role=role,
                phase=phase,
            )

            mock_context_pb2.GetContextRequest.assert_called_once_with(
                story_id="story-001",
                role="developer",  # Should be stripped
                phase="PLAN",
            )
        finally:
            mapper_module.context_pb2 = original_pb2



class TestContextGrpcMapperContextFromResponse:
    """Test extraction of context from proto response."""

    def test_context_from_response_success(self) -> None:
        """Test successful extraction of context from response."""
        response = MagicMock()
        response.context = "Formatted context blocks"

        context = ContextGrpcMapper.context_from_response(response)

        assert context == "Formatted context blocks"

    def test_context_from_response_empty_context(self) -> None:
        """Test extraction when context is empty string."""
        response = MagicMock()
        response.context = ""

        context = ContextGrpcMapper.context_from_response(response)

        assert context == ""

    def test_context_from_response_none_context(self) -> None:
        """Test extraction when context is None."""
        response = MagicMock()
        response.context = None

        context = ContextGrpcMapper.context_from_response(response)

        assert context == ""

    def test_context_from_response_with_multiline_context(self) -> None:
        """Test extraction of multi-line context."""
        multiline_context = """System: You are a developer
Context: Current story is story-001
Tools: Available tools are X, Y, Z"""

        response = MagicMock()
        response.context = multiline_context

        context = ContextGrpcMapper.context_from_response(response)

        assert context == multiline_context
        assert "\n" in context

    def test_context_from_response_rejects_none_response(self) -> None:
        """Test that mapper rejects None response."""
        with pytest.raises(ValueError, match="GetContextResponse cannot be None"):
            ContextGrpcMapper.context_from_response(None)  # type: ignore

