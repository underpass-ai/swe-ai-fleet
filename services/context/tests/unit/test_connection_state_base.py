"""Tests for ConnectionStateBase."""

from unittest.mock import AsyncMock

import pytest

from services.context.infrastructure.adapters.connection_state_base import (
    ConnectionStateBase,
)


class ConcreteConnectionHandler(ConnectionStateBase):
    """Concrete implementation for testing abstract base class."""

    def __init__(self) -> None:
        """Initialize concrete handler."""
        super().__init__()
        self._resource = None

    async def _close_connection(self) -> None:
        """Close connection implementation."""
        self._resource = None


class TestConnectionStateBaseInit:
    """Test ConnectionStateBase initialization."""

    def test_init_sets_connected_false(self) -> None:
        """Test that __init__ sets _connected to False."""
        handler = ConcreteConnectionHandler()
        assert handler._connected is False
        assert handler._is_connected() is False

    def test_init_can_be_called_by_subclass(self) -> None:
        """Test that subclasses can call super().__init__()."""
        handler = ConcreteConnectionHandler()
        assert hasattr(handler, "_connected")
        assert handler._connected is False


class TestConnectionStateBaseIsConnected:
    """Test _is_connected method."""

    def test_is_connected_returns_false_when_not_connected(self) -> None:
        """Test _is_connected returns False when not connected."""
        handler = ConcreteConnectionHandler()
        assert handler._is_connected() is False

    def test_is_connected_returns_true_when_connected(self) -> None:
        """Test _is_connected returns True when connected."""
        handler = ConcreteConnectionHandler()
        handler._connected = True
        assert handler._is_connected() is True


class TestConnectionStateBaseRequireConnected:
    """Test _require_connected method."""

    def test_require_connected_raises_when_not_connected(self) -> None:
        """Test _require_connected raises RuntimeError when not connected."""
        handler = ConcreteConnectionHandler()
        error_msg = "Not connected"

        with pytest.raises(RuntimeError, match="Not connected"):
            handler._require_connected(error_msg)

    def test_require_connected_passes_when_connected(self) -> None:
        """Test _require_connected does not raise when connected."""
        handler = ConcreteConnectionHandler()
        handler._connected = True
        error_msg = "Not connected"

        # Should not raise
        handler._require_connected(error_msg)

    def test_require_connected_uses_custom_error_message(self) -> None:
        """Test _require_connected uses provided error message."""
        handler = ConcreteConnectionHandler()
        custom_msg = "Custom connection error"

        with pytest.raises(RuntimeError, match="Custom connection error"):
            handler._require_connected(custom_msg)


class TestConnectionStateBaseClose:
    """Test close method."""

    @pytest.mark.asyncio
    async def test_close_calls_close_connection_when_connected(self) -> None:
        """Test close calls _close_connection when connected."""
        handler = ConcreteConnectionHandler()
        handler._connected = True
        handler._close_connection = AsyncMock()

        await handler.close()

        handler._close_connection.assert_awaited_once()
        assert handler._connected is False

    @pytest.mark.asyncio
    async def test_close_does_not_call_close_connection_when_not_connected(self) -> None:
        """Test close does not call _close_connection when not connected."""
        handler = ConcreteConnectionHandler()
        handler._connected = False
        handler._close_connection = AsyncMock()

        await handler.close()

        handler._close_connection.assert_not_awaited()
        assert handler._connected is False

    @pytest.mark.asyncio
    async def test_close_sets_connected_false_after_closing(self) -> None:
        """Test close sets _connected to False after closing."""
        handler = ConcreteConnectionHandler()
        handler._connected = True

        await handler.close()

        assert handler._connected is False

    @pytest.mark.asyncio
    async def test_close_handles_close_connection_exception(self) -> None:
        """Test close propagates exceptions from _close_connection."""
        handler = ConcreteConnectionHandler()
        handler._connected = True

        async def failing_close() -> None:
            raise RuntimeError("Close failed")

        handler._close_connection = failing_close

        with pytest.raises(RuntimeError, match="Close failed"):
            await handler.close()

        # State remains True if close fails (still connected)
        assert handler._connected is True


class TestConnectionStateBaseAbstract:
    """Test abstract method requirements."""

    def test_cannot_instantiate_base_class_directly(self) -> None:
        """Test that ConnectionStateBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ConnectionStateBase()  # type: ignore

    def test_subclass_must_implement_close_connection(self) -> None:
        """Test that subclasses must implement _close_connection."""

        class IncompleteHandler(ConnectionStateBase):
            """Handler missing _close_connection implementation."""

            pass

        with pytest.raises(TypeError):
            IncompleteHandler()  # type: ignore

