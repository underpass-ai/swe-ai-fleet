"""Base abstract class for connection state management.

This module provides a base class for handlers that manage connection state,
following the pattern of checking connection status before accessing resources.
"""

from abc import ABC, abstractmethod


class ConnectionStateBase(ABC):
    """Base class for handlers that manage connection state.

    Provides common functionality for:
    - Tracking connection state via `_connected` flag
    - Checking connection status via `_is_connected()` method
    - Validating connection before accessing resources

    Subclasses should:
    1. Call `super().__init__()` in `__init__` (sets `_connected = False`)
    2. Set `_connected = True` after successful connection
    3. Implement `_close_connection()` for connection-specific closing logic
    4. Use `_is_connected()` to check state
    5. Use `_require_connected()` in properties/methods that need connection
    """

    def __init__(self) -> None:
        """Initialize connection state base.

        Subclasses should call super().__init__() and set _connected = False.
        """
        self._connected = False

    def _is_connected(self) -> bool:
        """Check if connected.

        Returns:
            True if connected, False otherwise
        """
        return self._connected

    def _require_connected(self, error_message: str) -> None:
        """Require connection to be established.

        Raises:
            RuntimeError: If not connected

        Args:
            error_message: Error message to raise if not connected
        """
        if not self._connected:
            raise RuntimeError(error_message)

    @abstractmethod
    async def _close_connection(self) -> None:
        """Close the underlying connection.

        Subclasses must implement this method to perform connection-specific
        closing logic (e.g., closing sockets, releasing resources).

        This method is called by `close()` only when connected.
        """

    async def close(self) -> None:
        """Close connection and update state.

        Checks if connected, calls `_close_connection()` to perform
        connection-specific closing, then sets `_connected = False`.
        """
        if self._is_connected():
            await self._close_connection()
            self._connected = False

