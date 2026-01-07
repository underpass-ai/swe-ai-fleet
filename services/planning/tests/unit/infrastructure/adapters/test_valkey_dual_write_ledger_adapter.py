"""Unit tests for ValkeyDualWriteLedgerAdapter.

Tests use mocks to avoid hitting real Valkey/Redis.
Following repository rules: unit tests MUST NOT hit external systems.
"""

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from planning.application.dto.dual_write_operation import (
    DualWriteOperation,
    DualWriteStatus,
)
from planning.infrastructure.adapters.valkey_config import ValkeyConfig
from planning.infrastructure.adapters.valkey_dual_write_ledger_adapter import (
    ValkeyDualWriteLedgerAdapter,
)


class TestValkeyDualWriteLedgerAdapter:
    """Test cases for ValkeyDualWriteLedgerAdapter."""

    @pytest.fixture
    def mock_valkey_client(self) -> MagicMock:
        """Create a mock Valkey client."""
        client = MagicMock()
        client.ping.return_value = True
        client.get.return_value = None
        client.set.return_value = True
        client.sadd.return_value = 1
        client.srem.return_value = 1
        client.smembers.return_value = set()
        # Pipeline mock
        pipeline = MagicMock()
        pipeline.set = MagicMock(return_value=pipeline)
        pipeline.sadd = MagicMock(return_value=pipeline)
        pipeline.srem = MagicMock(return_value=pipeline)
        pipeline.execute = MagicMock(return_value=[True, 1])
        client.pipeline = MagicMock(return_value=pipeline)
        return client

    @pytest.fixture
    def valkey_config(self) -> ValkeyConfig:
        """Create Valkey configuration."""
        return ValkeyConfig(host="localhost", port=6379, db=0)

    @pytest.fixture
    def adapter(
        self,
        mock_valkey_client: MagicMock,
        valkey_config: ValkeyConfig,
    ) -> ValkeyDualWriteLedgerAdapter:
        """Create adapter with mocked Valkey client."""
        with patch(
            "planning.infrastructure.adapters.valkey_dual_write_ledger_adapter.valkey.Valkey"
        ) as mock_valkey_class:
            mock_valkey_class.return_value = mock_valkey_client
            adapter = ValkeyDualWriteLedgerAdapter(config=valkey_config)
            adapter.client = mock_valkey_client
            return adapter

    def test_init_success(
        self,
        mock_valkey_client: MagicMock,
        valkey_config: ValkeyConfig,
    ) -> None:
        """Test adapter initialization."""
        with patch(
            "planning.infrastructure.adapters.valkey_dual_write_ledger_adapter.valkey.Valkey"
        ) as mock_valkey_class:
            mock_valkey_class.return_value = mock_valkey_client
            adapter = ValkeyDualWriteLedgerAdapter(config=valkey_config)

            assert adapter.config == valkey_config
            mock_valkey_client.ping.assert_called_once()
            mock_valkey_class.assert_called_once_with(
                host=valkey_config.host,
                port=valkey_config.port,
                db=valkey_config.db,
                decode_responses=True,
            )

    def test_init_with_default_config(self, mock_valkey_client: MagicMock) -> None:
        """Test adapter initialization with default config."""
        with patch(
            "planning.infrastructure.adapters.valkey_dual_write_ledger_adapter.valkey.Valkey"
        ) as mock_valkey_class:
            mock_valkey_class.return_value = mock_valkey_client
            adapter = ValkeyDualWriteLedgerAdapter()

            assert adapter.config is not None
            mock_valkey_client.ping.assert_called_once()

    def test_close(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
        mock_valkey_client: MagicMock,
    ) -> None:
        """Test closing adapter connection."""
        adapter.close()

        mock_valkey_client.close.assert_called_once()

    def test_operation_key(self, adapter: ValkeyDualWriteLedgerAdapter) -> None:
        """Test operation key generation."""
        key = adapter._operation_key("test-op-123")

        assert key == "planning:dualwrite:test-op-123"

    def test_pending_set_key(self, adapter: ValkeyDualWriteLedgerAdapter) -> None:
        """Test pending set key generation."""
        key = adapter._pending_set_key()

        assert key == "planning:dualwrite:pending"

    @pytest.mark.asyncio
    async def test_record_pending_success(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
        mock_valkey_client: MagicMock,
    ) -> None:
        """Test recording a PENDING operation."""
        operation_id = "test-op-123"
        pipeline = mock_valkey_client.pipeline.return_value

        await adapter.record_pending(operation_id)

        # Verify pipeline operations
        mock_valkey_client.pipeline.assert_called_once()
        assert pipeline.set.called
        assert pipeline.sadd.called
        pipeline.execute.assert_called_once()

        # Verify key format
        set_call_args = pipeline.set.call_args
        assert "planning:dualwrite:test-op-123" in str(set_call_args)

    @pytest.mark.asyncio
    async def test_record_pending_empty_operation_id(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
    ) -> None:
        """Test that empty operation_id raises ValueError."""
        with pytest.raises(ValueError, match="operation_id cannot be empty"):
            await adapter.record_pending("")

    @pytest.mark.asyncio
    async def test_mark_completed_success(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
        mock_valkey_client: MagicMock,
    ) -> None:
        """Test marking an operation as COMPLETED."""
        operation_id = "test-op-123"
        timestamp = datetime.now(UTC).isoformat()

        # Mock existing operation
        existing_operation = {
            "operation_id": operation_id,
            "status": DualWriteStatus.PENDING.value,
            "attempts": 0,
            "last_error": None,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        mock_valkey_client.get.return_value = json.dumps(existing_operation)

        pipeline = mock_valkey_client.pipeline.return_value

        await adapter.mark_completed(operation_id)

        # Verify get was called to retrieve operation
        mock_valkey_client.get.assert_called_with(
            "planning:dualwrite:test-op-123"
        )

        # Verify pipeline operations
        mock_valkey_client.pipeline.assert_called_once()
        assert pipeline.set.called
        assert pipeline.srem.called
        pipeline.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_completed_operation_not_found(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
        mock_valkey_client: MagicMock,
    ) -> None:
        """Test marking COMPLETED when operation not found."""
        operation_id = "non-existent"
        mock_valkey_client.get.return_value = None

        # Should not raise, just log warning
        await adapter.mark_completed(operation_id)

        mock_valkey_client.get.assert_called_with(
            "planning:dualwrite:non-existent"
        )

    @pytest.mark.asyncio
    async def test_mark_completed_empty_operation_id(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
    ) -> None:
        """Test that empty operation_id raises ValueError."""
        with pytest.raises(ValueError, match="operation_id cannot be empty"):
            await adapter.mark_completed("")

    @pytest.mark.asyncio
    async def test_record_failure_success(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
        mock_valkey_client: MagicMock,
    ) -> None:
        """Test recording a failure for an operation."""
        operation_id = "test-op-123"
        error = "Connection timeout"
        timestamp = datetime.now(UTC).isoformat()

        # Mock existing operation
        existing_operation = {
            "operation_id": operation_id,
            "status": DualWriteStatus.PENDING.value,
            "attempts": 0,
            "last_error": None,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        mock_valkey_client.get.return_value = json.dumps(existing_operation)

        await adapter.record_failure(operation_id, error)

        # Verify get was called
        mock_valkey_client.get.assert_called_with(
            "planning:dualwrite:test-op-123"
        )

        # Verify set was called with updated operation
        mock_valkey_client.set.assert_called_once()
        set_call_args = mock_valkey_client.set.call_args[0]
        assert set_call_args[0] == "planning:dualwrite:test-op-123"

        # Verify updated operation has incremented attempts and error
        updated_operation = json.loads(set_call_args[1])
        assert updated_operation["attempts"] == 1
        assert updated_operation["last_error"] == error

    @pytest.mark.asyncio
    async def test_record_failure_empty_operation_id(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
    ) -> None:
        """Test that empty operation_id raises ValueError."""
        with pytest.raises(ValueError, match="operation_id cannot be empty"):
            await adapter.record_failure("", "error message")

    @pytest.mark.asyncio
    async def test_record_failure_empty_error(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
    ) -> None:
        """Test that empty error raises ValueError."""
        with pytest.raises(ValueError, match="error cannot be empty"):
            await adapter.record_failure("test-op", "")

    @pytest.mark.asyncio
    async def test_record_failure_operation_not_found(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
        mock_valkey_client: MagicMock,
    ) -> None:
        """Test recording failure when operation not found."""
        operation_id = "non-existent"
        mock_valkey_client.get.return_value = None

        # Should not raise, just log warning
        await adapter.record_failure(operation_id, "error")

        mock_valkey_client.get.assert_called_with(
            "planning:dualwrite:non-existent"
        )

    @pytest.mark.asyncio
    async def test_get_operation_found(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
        mock_valkey_client: MagicMock,
    ) -> None:
        """Test retrieving an operation that exists."""
        operation_id = "test-op-123"
        timestamp = datetime.now(UTC).isoformat()

        operation_data = {
            "operation_id": operation_id,
            "status": DualWriteStatus.PENDING.value,
            "attempts": 0,
            "last_error": None,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        mock_valkey_client.get.return_value = json.dumps(operation_data)

        result = await adapter.get_operation(operation_id)

        assert result is not None
        assert result.operation_id == operation_id
        assert result.status == DualWriteStatus.PENDING
        assert result.attempts == 0

        mock_valkey_client.get.assert_called_with(
            "planning:dualwrite:test-op-123"
        )

    @pytest.mark.asyncio
    async def test_get_operation_not_found(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
        mock_valkey_client: MagicMock,
    ) -> None:
        """Test retrieving an operation that doesn't exist."""
        operation_id = "non-existent"
        mock_valkey_client.get.return_value = None

        result = await adapter.get_operation(operation_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_operation_empty_operation_id(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
    ) -> None:
        """Test that empty operation_id raises ValueError."""
        with pytest.raises(ValueError, match="operation_id cannot be empty"):
            await adapter.get_operation("")

    @pytest.mark.asyncio
    async def test_list_pending_operations_empty(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
        mock_valkey_client: MagicMock,
    ) -> None:
        """Test listing pending operations when none exist."""
        mock_valkey_client.smembers.return_value = set()

        result = await adapter.list_pending_operations()

        assert result == []
        mock_valkey_client.smembers.assert_called_with(
            "planning:dualwrite:pending"
        )

    @pytest.mark.asyncio
    async def test_list_pending_operations_with_results(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
        mock_valkey_client: MagicMock,
    ) -> None:
        """Test listing pending operations."""
        operation_id_1 = "op-1"
        operation_id_2 = "op-2"
        timestamp = datetime.now(UTC).isoformat()

        # Mock pending set
        mock_valkey_client.smembers.return_value = {operation_id_1, operation_id_2}

        # Mock operations
        operation_data_1 = {
            "operation_id": operation_id_1,
            "status": DualWriteStatus.PENDING.value,
            "attempts": 0,
            "last_error": None,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        operation_data_2 = {
            "operation_id": operation_id_2,
            "status": DualWriteStatus.PENDING.value,
            "attempts": 1,
            "last_error": "Error",
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        def get_side_effect(key: str) -> str | None:
            if key == "planning:dualwrite:op-1":
                return json.dumps(operation_data_1)
            elif key == "planning:dualwrite:op-2":
                return json.dumps(operation_data_2)
            return None

        mock_valkey_client.get.side_effect = get_side_effect

        result = await adapter.list_pending_operations()

        assert len(result) == 2
        assert all(op.status == DualWriteStatus.PENDING for op in result)
        assert all(op.operation_id in {operation_id_1, operation_id_2} for op in result)

    @pytest.mark.asyncio
    async def test_list_pending_operations_with_limit(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
        mock_valkey_client: MagicMock,
    ) -> None:
        """Test listing pending operations with limit."""
        operation_ids = [f"op-{i}" for i in range(10)]
        timestamp = datetime.now(UTC).isoformat()

        mock_valkey_client.smembers.return_value = set(operation_ids)

        operation_data = {
            "operation_id": "op-0",
            "status": DualWriteStatus.PENDING.value,
            "attempts": 0,
            "last_error": None,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        mock_valkey_client.get.return_value = json.dumps(operation_data)

        result = await adapter.list_pending_operations(limit=5)

        # Should be limited to 5
        assert len(result) <= 5

    @pytest.mark.asyncio
    async def test_list_pending_operations_invalid_limit(
        self,
        adapter: ValkeyDualWriteLedgerAdapter,
    ) -> None:
        """Test that invalid limit raises ValueError."""
        with pytest.raises(ValueError, match="limit must be positive"):
            await adapter.list_pending_operations(limit=0)

        with pytest.raises(ValueError, match="limit must be positive"):
            await adapter.list_pending_operations(limit=-1)
