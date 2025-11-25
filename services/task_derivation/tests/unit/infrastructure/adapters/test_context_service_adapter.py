"""Tests for ContextServiceAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.domain.value_objects.task_derivation.context.derivation_phase import (
    DerivationPhase,
)
from task_derivation.infrastructure.adapters.context_service_adapter import (
    ContextServiceAdapter,
)


class TestContextServiceAdapterInit:
    """Test initialization of ContextServiceAdapter."""

    def test_init_valid_address(self) -> None:
        """Test successful initialization with valid address."""
        adapter = ContextServiceAdapter(address="context-service:50054")
        assert adapter._address == "context-service:50054"
        assert adapter._timeout == pytest.approx(5.0)

    def test_init_imports_grpc_stub_correctly(self) -> None:
        """Test that context_pb2_grpc can be imported and stub class exists.

        This test ensures that the gRPC stubs are properly generated.
        If this fails, it means the Dockerfile is missing context.proto generation.

        Note: In test environment, stubs may be mocked in conftest.py.
        This test verifies the mock is correctly set up.
        """
        # Try to import the module (should work if stubs are generated or mocked)
        try:
            from task_derivation.gen import context_pb2_grpc
            # Verify that ContextServiceStub class exists (either real or mocked)
            assert hasattr(context_pb2_grpc, "ContextServiceStub"), \
                "ContextServiceStub not found in context_pb2_grpc. " \
                "Check that context.proto is being generated in Dockerfile " \
                "or that conftest.py mocks ContextServiceStub correctly."
        except ImportError as e:
            pytest.fail(
                f"Failed to import context_pb2_grpc: {e}. "
                "This indicates that context.proto stubs are not being generated. "
                "Check Dockerfile for context.proto generation step."
            )

    def test_init_with_custom_timeout(self) -> None:
        """Test initialization with custom timeout."""
        adapter = ContextServiceAdapter(
            address="context-service:50054",
            timeout_seconds=10.0,
        )
        assert adapter._timeout == pytest.approx(10.0)

    def test_init_rejects_empty_address(self) -> None:
        """Test that initialization rejects empty address."""
        with pytest.raises(ValueError, match="address cannot be empty"):
            ContextServiceAdapter(address="")

    def test_init_rejects_whitespace_address(self) -> None:
        """Test that initialization rejects whitespace-only address."""
        with pytest.raises(ValueError, match="address cannot be empty"):
            ContextServiceAdapter(address="   ")


class TestContextServiceAdapterGetContext:
    """Test get_context method."""

    @pytest.mark.asyncio
    async def test_get_context_calls_grpc_service(self, monkeypatch) -> None:
        """Test get_context calls gRPC service and returns context."""
        # Create mock response
        mock_response = MagicMock()
        mock_response.context = "Formatted context blocks"
        mock_response.token_count = 250

        # Create mock stub
        mock_stub = AsyncMock()
        mock_stub.GetContext = AsyncMock(return_value=mock_response)

        # Mock the gRPC channel creation
        mock_channel = AsyncMock()

        # Patch the adapter's internal stub creation
        def mock_secure_channel(address, credentials):
            return mock_channel

        import grpc.aio as aio_grpc
        monkeypatch.setattr(aio_grpc, "secure_channel", mock_secure_channel)

        # Mock ContextServiceStub creation to verify it's called
        # This ensures we're actually using context_pb2_grpc.ContextServiceStub
        # Note: context_pb2_grpc may be mocked in conftest.py, so we ensure ContextServiceStub exists
        from task_derivation.gen import context_pb2_grpc

        # Ensure ContextServiceStub exists (either from mock or real stub)
        if not hasattr(context_pb2_grpc, "ContextServiceStub"):
            # If not present, add it (shouldn't happen if conftest.py is correct)
            context_pb2_grpc.ContextServiceStub = MagicMock

        mock_stub_class = MagicMock(return_value=mock_stub)
        monkeypatch.setattr(context_pb2_grpc, "ContextServiceStub", mock_stub_class)

        adapter = ContextServiceAdapter(address="context-service:50054")
        # Don't inject stub directly - let it be created naturally to verify stub creation works
        adapter._channel = mock_channel  # Set channel so stub creation happens

        story_id = StoryId("story-001")
        role = ContextRole("developer")
        phase = DerivationPhase.PLAN

        result = await adapter.get_context(story_id, role, phase)

        assert result == "Formatted context blocks"
        # Verify stub was created using context_pb2_grpc.ContextServiceStub
        mock_stub_class.assert_called_once_with(mock_channel)
        mock_stub.GetContext.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_context_handles_error(self) -> None:
        """Test get_context propagates errors."""
        mock_stub = AsyncMock()
        mock_stub.GetContext = AsyncMock(
            side_effect=RuntimeError("Context service unavailable")
        )

        adapter = ContextServiceAdapter(address="context-service:50054")
        adapter._stub = mock_stub

        story_id = StoryId("story-001")
        role = ContextRole("developer")

        with pytest.raises(RuntimeError, match="Context service unavailable"):
            await adapter.get_context(story_id, role)

    @pytest.mark.asyncio
    async def test_get_context_logs_success(self, caplog) -> None:
        """Test that get_context logs successful calls."""
        import logging

        caplog.set_level(logging.INFO)

        mock_response = MagicMock()
        mock_response.context = "Context"
        mock_response.token_count = 200

        mock_stub = AsyncMock()
        mock_stub.GetContext = AsyncMock(return_value=mock_response)

        adapter = ContextServiceAdapter(address="context-service:50054")
        adapter._stub = mock_stub

        story_id = StoryId("story-001")
        role = ContextRole("developer")

        await adapter.get_context(story_id, role)

        assert "Fetching context" in caplog.text
        assert "Successfully fetched context" in caplog.text

    @pytest.mark.asyncio
    async def test_get_context_with_custom_phase(self) -> None:
        """Test get_context with custom derivation phase."""
        mock_response = MagicMock()
        mock_response.context = "Context for test phase"
        mock_response.token_count = 150

        mock_stub = AsyncMock()
        mock_stub.GetContext = AsyncMock(return_value=mock_response)

        adapter = ContextServiceAdapter(address="context-service:50054")
        adapter._stub = mock_stub

        story_id = StoryId("story-001")
        role = ContextRole("qa")
        phase = DerivationPhase.EXECUTION

        result = await adapter.get_context(story_id, role, phase)

        assert result == "Context for test phase"
        call_args = mock_stub.GetContext.call_args
        assert call_args is not None


class TestContextServiceAdapterClose:
    """Test close method."""

    @pytest.mark.asyncio
    async def test_close_with_open_channel(self) -> None:
        """Test close closes the gRPC channel."""
        mock_channel = AsyncMock()
        adapter = ContextServiceAdapter(address="context-service:50054")
        adapter._channel = mock_channel

        await adapter.close()

        mock_channel.close.assert_awaited_once()
        assert adapter._channel is None

    @pytest.mark.asyncio
    async def test_close_without_channel(self) -> None:
        """Test close when channel is None."""
        adapter = ContextServiceAdapter(address="context-service:50054")

        # Should not raise
        await adapter.close()

        assert adapter._channel is None

