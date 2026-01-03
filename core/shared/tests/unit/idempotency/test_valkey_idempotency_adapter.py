"""Unit tests for ValkeyIdempotencyAdapter.

Tests use mocks to avoid hitting real Valkey/Redis.
Following repository rules: unit tests MUST NOT hit external systems.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.shared.idempotency.idempotency_state import IdempotencyState
from core.shared.idempotency.infrastructure.valkey_idempotency_adapter import (
    ValkeyIdempotencyAdapter,
)


class TestValkeyIdempotencyAdapter:
    """Test cases for ValkeyIdempotencyAdapter."""

    @pytest.fixture
    def mock_valkey_client(self):
        """Create a mock Valkey client."""
        client = MagicMock()
        client.ping.return_value = True
        return client

    @pytest.fixture
    def adapter(self, mock_valkey_client):
        """Create adapter with mocked Valkey client."""
        with patch("core.shared.idempotency.infrastructure.valkey_idempotency_adapter.valkey.Valkey") as mock_valkey_class:
            mock_valkey_class.return_value = mock_valkey_client
            adapter = ValkeyIdempotencyAdapter(host="localhost", port=6379)
            adapter._client = mock_valkey_client
            return adapter

    def test_init_success(self, mock_valkey_client):
        """Test successful adapter initialization."""
        with patch("core.shared.idempotency.infrastructure.valkey_idempotency_adapter.valkey.Valkey") as mock_valkey_class:
            mock_valkey_class.return_value = mock_valkey_client
            adapter = ValkeyIdempotencyAdapter(host="localhost", port=6379)

            assert adapter._host == "localhost"
            assert adapter._port == 6379
            mock_valkey_client.ping.assert_called_once()

    def test_init_connection_failure(self, mock_valkey_client):
        """Test adapter initialization with connection failure."""
        mock_valkey_client.ping.side_effect = Exception("Connection failed")

        with patch("core.shared.idempotency.infrastructure.valkey_idempotency_adapter.valkey.Valkey") as mock_valkey_class:
            mock_valkey_class.return_value = mock_valkey_client

            with pytest.raises(RuntimeError, match="Valkey connection failed"):
                ValkeyIdempotencyAdapter(host="localhost", port=6379)

    def test_close(self, adapter, mock_valkey_client):
        """Test closing adapter connection."""
        adapter.close()

        mock_valkey_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_status_not_found(self, adapter, mock_valkey_client):
        """Test check_status when key doesn't exist."""
        mock_valkey_client.get.return_value = None

        result = await adapter.check_status("test-key")

        assert result is None
        mock_valkey_client.get.assert_called_once_with("idempotency:test-key")

    @pytest.mark.asyncio
    async def test_check_status_completed(self, adapter, mock_valkey_client):
        """Test check_status when key exists with COMPLETED state."""
        state_data = {
            "state": "COMPLETED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        mock_valkey_client.get.return_value = json.dumps(state_data)

        result = await adapter.check_status("test-key")

        assert result == IdempotencyState.COMPLETED

    @pytest.mark.asyncio
    async def test_check_status_in_progress(self, adapter, mock_valkey_client):
        """Test check_status when key exists with IN_PROGRESS state."""
        state_data = {
            "state": "IN_PROGRESS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        mock_valkey_client.get.return_value = json.dumps(state_data)

        result = await adapter.check_status("test-key")

        assert result == IdempotencyState.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_check_status_invalid_key(self, adapter):
        """Test check_status with empty key raises ValueError."""
        with pytest.raises(ValueError, match="idempotency_key cannot be empty"):
            await adapter.check_status("")

    @pytest.mark.asyncio
    async def test_check_status_storage_error(self, adapter, mock_valkey_client):
        """Test check_status propagates storage errors."""
        mock_valkey_client.get.side_effect = Exception("Storage error")

        with pytest.raises(Exception, match="Storage error"):
            await adapter.check_status("test-key")

    @pytest.mark.asyncio
    async def test_mark_in_progress_success(self, adapter, mock_valkey_client):
        """Test mark_in_progress successfully marks key."""
        mock_valkey_client.set.return_value = True  # SETNX returns True

        result = await adapter.mark_in_progress("test-key", ttl_seconds=300)

        assert result is True
        mock_valkey_client.set.assert_called_once()
        call_args = mock_valkey_client.set.call_args
        assert call_args[0][0] == "idempotency:test-key"
        assert call_args[1]["ex"] == 300
        assert call_args[1]["nx"] is True

    @pytest.mark.asyncio
    async def test_mark_in_progress_already_exists(self, adapter, mock_valkey_client):
        """Test mark_in_progress when key already exists."""
        mock_valkey_client.set.return_value = False  # SETNX returns False
        # Mock check_status to return COMPLETED
        state_data = {
            "state": "COMPLETED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        mock_valkey_client.get.return_value = json.dumps(state_data)

        result = await adapter.mark_in_progress("test-key", ttl_seconds=300)

        assert result is False

    @pytest.mark.asyncio
    async def test_mark_in_progress_invalid_key(self, adapter):
        """Test mark_in_progress with empty key raises ValueError."""
        with pytest.raises(ValueError, match="idempotency_key cannot be empty"):
            await adapter.mark_in_progress("", ttl_seconds=300)

    @pytest.mark.asyncio
    async def test_mark_in_progress_invalid_ttl(self, adapter):
        """Test mark_in_progress with invalid TTL raises ValueError."""
        with pytest.raises(ValueError, match="ttl_seconds must be positive"):
            await adapter.mark_in_progress("test-key", ttl_seconds=0)

        with pytest.raises(ValueError, match="ttl_seconds must be positive"):
            await adapter.mark_in_progress("test-key", ttl_seconds=-1)

    @pytest.mark.asyncio
    async def test_mark_completed_without_ttl(self, adapter, mock_valkey_client):
        """Test mark_completed without TTL (keep forever)."""
        await adapter.mark_completed("test-key")

        mock_valkey_client.set.assert_called_once()
        call_args = mock_valkey_client.set.call_args
        assert call_args[0][0] == "idempotency:test-key"
        assert "ex" not in call_args[1]  # No TTL

    @pytest.mark.asyncio
    async def test_mark_completed_with_ttl(self, adapter, mock_valkey_client):
        """Test mark_completed with TTL."""
        await adapter.mark_completed("test-key", ttl_seconds=3600)

        mock_valkey_client.set.assert_called_once()
        call_args = mock_valkey_client.set.call_args
        assert call_args[0][0] == "idempotency:test-key"
        assert call_args[1]["ex"] == 3600

    @pytest.mark.asyncio
    async def test_mark_completed_invalid_key(self, adapter):
        """Test mark_completed with empty key raises ValueError."""
        with pytest.raises(ValueError, match="idempotency_key cannot be empty"):
            await adapter.mark_completed("")

    @pytest.mark.asyncio
    async def test_is_stale_not_found(self, adapter, mock_valkey_client):
        """Test is_stale when key doesn't exist."""
        mock_valkey_client.get.return_value = None

        result = await adapter.is_stale("test-key", max_age_seconds=600)

        assert result is False

    @pytest.mark.asyncio
    async def test_is_stale_completed_state(self, adapter, mock_valkey_client):
        """Test is_stale when state is COMPLETED (not stale)."""
        state_data = {
            "state": "COMPLETED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        mock_valkey_client.get.return_value = json.dumps(state_data)

        result = await adapter.is_stale("test-key", max_age_seconds=600)

        assert result is False

    @pytest.mark.asyncio
    async def test_is_stale_in_progress_fresh(self, adapter, mock_valkey_client):
        """Test is_stale when IN_PROGRESS is fresh (not stale)."""
        # Timestamp 1 minute ago (fresh)
        timestamp = datetime.now(timezone.utc).replace(microsecond=0)
        state_data = {
            "state": "IN_PROGRESS",
            "timestamp": timestamp.isoformat(),
        }
        mock_valkey_client.get.return_value = json.dumps(state_data)

        result = await adapter.is_stale("test-key", max_age_seconds=600)

        assert result is False

    @pytest.mark.asyncio
    async def test_is_stale_in_progress_old(self, adapter, mock_valkey_client):
        """Test is_stale when IN_PROGRESS is old (stale)."""
        # Timestamp 20 minutes ago (stale if max_age is 10 minutes)
        timestamp = datetime.now(timezone.utc).replace(microsecond=0)
        from datetime import timedelta

        old_timestamp = timestamp - timedelta(seconds=1200)  # 20 minutes
        state_data = {
            "state": "IN_PROGRESS",
            "timestamp": old_timestamp.isoformat(),
        }
        mock_valkey_client.get.return_value = json.dumps(state_data)

        result = await adapter.is_stale("test-key", max_age_seconds=600)

        assert result is True

    @pytest.mark.asyncio
    async def test_is_stale_invalid_key(self, adapter):
        """Test is_stale with empty key raises ValueError."""
        with pytest.raises(ValueError, match="idempotency_key cannot be empty"):
            await adapter.is_stale("", max_age_seconds=600)

    @pytest.mark.asyncio
    async def test_is_stale_invalid_max_age(self, adapter):
        """Test is_stale with invalid max_age raises ValueError."""
        with pytest.raises(ValueError, match="max_age_seconds must be positive"):
            await adapter.is_stale("test-key", max_age_seconds=0)

        with pytest.raises(ValueError, match="max_age_seconds must be positive"):
            await adapter.is_stale("test-key", max_age_seconds=-1)

    @pytest.mark.asyncio
    async def test_is_stale_invalid_timestamp(self, adapter, mock_valkey_client):
        """Test is_stale with invalid timestamp format (considers stale)."""
        state_data = {
            "state": "IN_PROGRESS",
            "timestamp": "invalid-timestamp",
        }
        mock_valkey_client.get.return_value = json.dumps(state_data)

        result = await adapter.is_stale("test-key", max_age_seconds=600)

        # Invalid timestamp is considered stale (safer to retry)
        assert result is True
