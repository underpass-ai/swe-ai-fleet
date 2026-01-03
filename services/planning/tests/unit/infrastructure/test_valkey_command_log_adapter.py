"""Unit tests for ValkeyCommandLogAdapter.

Tests use mocks to avoid hitting real Valkey/Redis.
Following repository rules: unit tests MUST NOT hit external systems.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from planning.infrastructure.adapters.valkey_command_log_adapter import (
    ERROR_REQUEST_ID_EMPTY,
    ValkeyCommandLogAdapter,
)
from planning.infrastructure.adapters.valkey_config import ValkeyConfig


class TestValkeyCommandLogAdapter:
    """Test cases for ValkeyCommandLogAdapter."""

    @pytest.fixture
    def mock_valkey_client(self) -> MagicMock:
        """Create a mock Valkey client."""
        client = MagicMock()
        client.ping.return_value = True
        return client

    @pytest.fixture
    def valkey_config(self) -> ValkeyConfig:
        """Create Valkey configuration."""
        return ValkeyConfig(host="localhost", port=6379, db=0)

    @pytest.fixture
    def adapter(self, mock_valkey_client: MagicMock, valkey_config: ValkeyConfig) -> ValkeyCommandLogAdapter:
        """Create adapter with mocked Valkey client."""
        with patch("planning.infrastructure.adapters.valkey_command_log_adapter.valkey.Valkey") as mock_valkey_class:
            mock_valkey_class.return_value = mock_valkey_client
            adapter = ValkeyCommandLogAdapter(config=valkey_config)
            adapter.client = mock_valkey_client
            return adapter

    def test_init_success(self, mock_valkey_client: MagicMock, valkey_config: ValkeyConfig) -> None:
        """Test successful adapter initialization."""
        with patch("planning.infrastructure.adapters.valkey_command_log_adapter.valkey.Valkey") as mock_valkey_class:
            mock_valkey_class.return_value = mock_valkey_client
            adapter = ValkeyCommandLogAdapter(config=valkey_config)

            assert adapter.config == valkey_config
            mock_valkey_client.ping.assert_called_once()
            mock_valkey_class.assert_called_once_with(
                host=valkey_config.host,
                port=valkey_config.port,
                db=valkey_config.db,
                decode_responses=False,
            )

    def test_init_with_default_config(self, mock_valkey_client: MagicMock) -> None:
        """Test adapter initialization with default config."""
        with patch("planning.infrastructure.adapters.valkey_command_log_adapter.valkey.Valkey") as mock_valkey_class:
            mock_valkey_class.return_value = mock_valkey_client
            adapter = ValkeyCommandLogAdapter()

            assert adapter.config is not None
            mock_valkey_client.ping.assert_called_once()

    def test_close(self, adapter: ValkeyCommandLogAdapter, mock_valkey_client: MagicMock) -> None:
        """Test closing adapter connection."""
        adapter.close()

        mock_valkey_client.close.assert_called_once()

    def test_command_log_key(self, adapter: ValkeyCommandLogAdapter) -> None:
        """Test command log key generation."""
        key = adapter._command_log_key("test-request-id")

        assert key == "planning:cmd:test-request-id"

    @pytest.mark.asyncio
    async def test_get_response_not_found(self, adapter: ValkeyCommandLogAdapter, mock_valkey_client: MagicMock) -> None:
        """Test get_response when key doesn't exist."""
        mock_valkey_client.get.return_value = None

        result = await adapter.get_response("test-request-id")

        assert result is None
        mock_valkey_client.get.assert_called_once_with("planning:cmd:test-request-id")

    @pytest.mark.asyncio
    async def test_get_response_found(self, adapter: ValkeyCommandLogAdapter, mock_valkey_client: MagicMock) -> None:
        """Test get_response when key exists."""
        response_bytes = b"serialized_response_bytes"
        mock_valkey_client.get.return_value = response_bytes

        result = await adapter.get_response("test-request-id")

        assert result == response_bytes
        mock_valkey_client.get.assert_called_once_with("planning:cmd:test-request-id")

    @pytest.mark.asyncio
    async def test_get_response_strips_request_id(self, adapter: ValkeyCommandLogAdapter, mock_valkey_client: MagicMock) -> None:
        """Test get_response strips whitespace from request_id."""
        response_bytes = b"serialized_response_bytes"
        mock_valkey_client.get.return_value = response_bytes

        await adapter.get_response("  test-request-id  ")

        mock_valkey_client.get.assert_called_once_with("planning:cmd:test-request-id")

    @pytest.mark.asyncio
    async def test_get_response_empty_request_id(self, adapter: ValkeyCommandLogAdapter) -> None:
        """Test get_response raises ValueError for empty request_id."""
        with pytest.raises(ValueError, match=ERROR_REQUEST_ID_EMPTY):
            await adapter.get_response("")

    @pytest.mark.asyncio
    async def test_get_response_whitespace_only_request_id(self, adapter: ValkeyCommandLogAdapter) -> None:
        """Test get_response raises ValueError for whitespace-only request_id."""
        with pytest.raises(ValueError, match=ERROR_REQUEST_ID_EMPTY):
            await adapter.get_response("   ")

    @pytest.mark.asyncio
    async def test_get_response_storage_error(self, adapter: ValkeyCommandLogAdapter, mock_valkey_client: MagicMock) -> None:
        """Test get_response propagates storage errors."""
        mock_valkey_client.get.side_effect = Exception("Storage error")

        with pytest.raises(Exception, match="Storage error"):
            await adapter.get_response("test-request-id")

    @pytest.mark.asyncio
    async def test_store_response_success(self, adapter: ValkeyCommandLogAdapter, mock_valkey_client: MagicMock) -> None:
        """Test store_response successfully stores response."""
        response_bytes = b"serialized_response_bytes"

        await adapter.store_response("test-request-id", response_bytes)

        mock_valkey_client.set.assert_called_once_with("planning:cmd:test-request-id", response_bytes)

    @pytest.mark.asyncio
    async def test_store_response_strips_request_id(self, adapter: ValkeyCommandLogAdapter, mock_valkey_client: MagicMock) -> None:
        """Test store_response strips whitespace from request_id."""
        response_bytes = b"serialized_response_bytes"

        await adapter.store_response("  test-request-id  ", response_bytes)

        mock_valkey_client.set.assert_called_once_with("planning:cmd:test-request-id", response_bytes)

    @pytest.mark.asyncio
    async def test_store_response_empty_request_id(self, adapter: ValkeyCommandLogAdapter) -> None:
        """Test store_response raises ValueError for empty request_id."""
        with pytest.raises(ValueError, match=ERROR_REQUEST_ID_EMPTY):
            await adapter.store_response("", b"response_bytes")

    @pytest.mark.asyncio
    async def test_store_response_whitespace_only_request_id(self, adapter: ValkeyCommandLogAdapter) -> None:
        """Test store_response raises ValueError for whitespace-only request_id."""
        with pytest.raises(ValueError, match=ERROR_REQUEST_ID_EMPTY):
            await adapter.store_response("   ", b"response_bytes")

    @pytest.mark.asyncio
    async def test_store_response_empty_response_bytes(self, adapter: ValkeyCommandLogAdapter) -> None:
        """Test store_response raises ValueError for empty response_bytes."""
        with pytest.raises(ValueError, match="response_bytes cannot be empty"):
            await adapter.store_response("test-request-id", b"")

    @pytest.mark.asyncio
    async def test_store_response_storage_error(self, adapter: ValkeyCommandLogAdapter, mock_valkey_client: MagicMock) -> None:
        """Test store_response propagates storage errors."""
        mock_valkey_client.set.side_effect = Exception("Storage error")

        with pytest.raises(Exception, match="Storage error"):
            await adapter.store_response("test-request-id", b"response_bytes")

    @pytest.mark.asyncio
    async def test_get_response_calls_valkey_get(self, adapter: ValkeyCommandLogAdapter, mock_valkey_client: MagicMock) -> None:
        """Test get_response calls Valkey get method."""
        mock_valkey_client.get.return_value = b"response_bytes"

        result = await adapter.get_response("test-request-id")

        assert result == b"response_bytes"
        # Verify get was called (asyncio.to_thread wraps it)
        assert mock_valkey_client.get.called

    @pytest.mark.asyncio
    async def test_store_response_calls_valkey_set(self, adapter: ValkeyCommandLogAdapter, mock_valkey_client: MagicMock) -> None:
        """Test store_response calls Valkey set method."""
        response_bytes = b"response_bytes"

        await adapter.store_response("test-request-id", response_bytes)

        # Verify set was called (asyncio.to_thread wraps it)
        assert mock_valkey_client.set.called
