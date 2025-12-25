"""Unit tests for ValkeyStorageAdapter - interface verification only.

Note: Full functionality testing of Valkey adapter requires integration tests
with real Valkey instance due to async Redis operations and serialization logic.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from planning.infrastructure.adapters.valkey_adapter import ValkeyStorageAdapter
from planning.infrastructure.adapters.valkey_config import ValkeyConfig


@pytest.fixture
def valkey_config():
    """Create Valkey configuration."""
    return ValkeyConfig(
        host="localhost",
        port=6379,
        db=0,
    )


@pytest.mark.asyncio
async def test_valkey_adapter_init(valkey_config):
    """Test ValkeyStorageAdapter initialization."""
    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        ValkeyStorageAdapter(config=valkey_config)

        # Verify Valkey client was created with correct parameters
        mock_valkey_class.assert_called_once_with(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True,
        )
        mock_client.ping.assert_called_once()


def test_valkey_adapter_has_required_methods(valkey_config):
    """Test ValkeyStorageAdapter has all required methods (interface verification)."""
    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)

        # Verify adapter has all required async methods (stories)
        assert hasattr(adapter, 'save_story')
        assert hasattr(adapter, 'get_story')
        assert hasattr(adapter, 'list_stories')
        assert hasattr(adapter, 'update_story')
        assert hasattr(adapter, 'delete_story')
        # Verify adapter has all required async methods (projects)
        assert hasattr(adapter, 'save_project')
        assert hasattr(adapter, 'get_project')
        assert hasattr(adapter, 'list_projects')
        # Verify adapter has all required async methods (epics)
        assert hasattr(adapter, 'save_epic')
        assert hasattr(adapter, 'get_epic')
        assert hasattr(adapter, 'list_epics')
        assert hasattr(adapter, 'close')

        # Verify they are async (except close)
        import inspect
        assert inspect.iscoroutinefunction(adapter.save_story)
        assert inspect.iscoroutinefunction(adapter.get_story)
        assert inspect.iscoroutinefunction(adapter.list_stories)
        assert inspect.iscoroutinefunction(adapter.update_story)
        assert inspect.iscoroutinefunction(adapter.delete_story)
        assert inspect.iscoroutinefunction(adapter.save_project)
        assert inspect.iscoroutinefunction(adapter.get_project)
        assert inspect.iscoroutinefunction(adapter.list_projects)
        assert inspect.iscoroutinefunction(adapter.save_epic)
        assert inspect.iscoroutinefunction(adapter.get_epic)
        assert inspect.iscoroutinefunction(adapter.list_epics)


@pytest.mark.asyncio
async def test_valkey_adapter_close(valkey_config):
    """Test close closes Valkey connection."""
    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)
        adapter.close()

        mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_set_json(valkey_config):
    """Test set_json stores JSON data."""
    import json

    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = None
            test_data = {"key": "value", "number": 42}

            await adapter.set_json("test:key", test_data, ttl_seconds=3600)

            mock_to_thread.assert_called_once()
            call_args = mock_to_thread.call_args
            assert call_args[0][0] == mock_client.set
            assert call_args[0][1] == "test:key"
            assert json.loads(call_args[0][2]) == test_data
            assert call_args[1]["ex"] == 3600


@pytest.mark.asyncio
async def test_set_json_without_ttl(valkey_config):
    """Test set_json without TTL."""
    import json

    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = None
            test_data = {"key": "value"}

            await adapter.set_json("test:key", test_data)

            mock_to_thread.assert_called_once()
            call_args = mock_to_thread.call_args
            assert call_args[0][0] == mock_client.set
            assert call_args[0][1] == "test:key"
            assert json.loads(call_args[0][2]) == test_data
            assert call_args[1]["ex"] is None  # No TTL


@pytest.mark.asyncio
async def test_get_json(valkey_config):
    """Test get_json retrieves JSON data."""
    import json

    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)

        test_data = {"key": "value", "number": 42}
        json_str = json.dumps(test_data)

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = json_str

            result = await adapter.get_json("test:key")

            assert result == test_data
            mock_to_thread.assert_called_once_with(mock_client.get, "test:key")


@pytest.mark.asyncio
async def test_get_json_not_found(valkey_config):
    """Test get_json returns None when key not found."""
    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = None

            result = await adapter.get_json("test:key")

            assert result is None


@pytest.mark.asyncio
async def test_save_ceremony_story_po_approval(valkey_config):
    """Test save_ceremony_story_po_approval stores PO approval data."""
    from datetime import UTC, datetime
    from unittest.mock import MagicMock, patch

    from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
        BacklogReviewCeremonyId,
    )
    from planning.domain.value_objects.identifiers.story_id import StoryId

    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)

        ceremony_id = BacklogReviewCeremonyId("BRC-001")
        story_id = StoryId("ST-001")
        approved_at = datetime.now(UTC).isoformat()

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = None

            await adapter.save_ceremony_story_po_approval(
                ceremony_id=ceremony_id,
                story_id=story_id,
                po_notes="Approved with notes",
                approved_by="po-user",
                approved_at=approved_at,
                po_concerns="Some concerns",
                priority_adjustment="HIGH",
                po_priority_reason="Critical",
            )

            mock_to_thread.assert_called_once()
            call_args = mock_to_thread.call_args
            assert call_args[0][0] == mock_client.hset
            assert call_args[0][1] == "planning:ceremony:BRC-001:story:ST-001:po_approval"
            assert "mapping" in call_args[1]
            mapping = call_args[1]["mapping"]
            assert mapping["po_notes"] == "Approved with notes"
            assert mapping["approved_by"] == "po-user"
            assert mapping["approved_at"] == approved_at
            assert mapping["po_concerns"] == "Some concerns"
            assert mapping["priority_adjustment"] == "HIGH"
            assert mapping["po_priority_reason"] == "Critical"


@pytest.mark.asyncio
async def test_save_ceremony_story_po_approval_minimal(valkey_config):
    """Test save_ceremony_story_po_approval with minimal required fields."""
    from datetime import UTC, datetime
    from unittest.mock import MagicMock, patch

    from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
        BacklogReviewCeremonyId,
    )
    from planning.domain.value_objects.identifiers.story_id import StoryId

    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)

        ceremony_id = BacklogReviewCeremonyId("BRC-001")
        story_id = StoryId("ST-001")
        approved_at = datetime.now(UTC).isoformat()

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = None

            await adapter.save_ceremony_story_po_approval(
                ceremony_id=ceremony_id,
                story_id=story_id,
                po_notes="Approved",
                approved_by="po-user",
                approved_at=approved_at,
            )

            mock_to_thread.assert_called_once()
            call_args = mock_to_thread.call_args
            assert call_args[0][0] == mock_client.hset
            assert "mapping" in call_args[1]
            mapping = call_args[1]["mapping"]
            assert "po_notes" in mapping
            assert "approved_by" in mapping
            assert "approved_at" in mapping
            assert "po_concerns" not in mapping
            assert "priority_adjustment" not in mapping


@pytest.mark.asyncio
async def test_get_ceremony_story_po_approval(valkey_config):
    """Test get_ceremony_story_po_approval retrieves PO approval data."""
    from datetime import UTC, datetime
    from unittest.mock import MagicMock, patch

    from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
        BacklogReviewCeremonyId,
    )
    from planning.domain.value_objects.identifiers.story_id import StoryId

    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)

        ceremony_id = BacklogReviewCeremonyId("BRC-001")
        story_id = StoryId("ST-001")
        approved_at = datetime.now(UTC).isoformat()

        test_data = {
            "po_notes": "Approved with notes",
            "approved_by": "po-user",
            "approved_at": approved_at,
            "po_concerns": "Some concerns",
            "priority_adjustment": "HIGH",
            "po_priority_reason": "Critical",
        }

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = test_data

            result = await adapter.get_ceremony_story_po_approval(
                ceremony_id=ceremony_id, story_id=story_id
            )

            assert result == test_data
            mock_to_thread.assert_called_once()


@pytest.mark.asyncio
async def test_get_ceremony_story_po_approval_not_found(valkey_config):
    """Test get_ceremony_story_po_approval returns None when not found."""
    from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
        BacklogReviewCeremonyId,
    )
    from planning.domain.value_objects.identifiers.story_id import StoryId

    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)

        ceremony_id = BacklogReviewCeremonyId("BRC-001")
        story_id = StoryId("ST-001")

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = {}

            result = await adapter.get_ceremony_story_po_approval(
                ceremony_id=ceremony_id, story_id=story_id
            )

            assert result is None


@pytest.mark.asyncio
async def test_get_ceremony_story_po_approval_with_bytes(valkey_config):
    """Test get_ceremony_story_po_approval handles bytes decoding."""
    from datetime import UTC, datetime

    from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
        BacklogReviewCeremonyId,
    )
    from planning.domain.value_objects.identifiers.story_id import StoryId

    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)

        ceremony_id = BacklogReviewCeremonyId("BRC-001")
        story_id = StoryId("ST-001")

        test_data = {
            b"po_notes": b"Approved with notes",
            b"approved_by": b"po-user",
            b"approved_at": datetime.now(UTC).isoformat().encode("utf-8"),
        }

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = test_data

            result = await adapter.get_ceremony_story_po_approval(
                ceremony_id=ceremony_id, story_id=story_id
            )

            assert result is not None
            assert result["po_notes"] == "Approved with notes"
            assert result["approved_by"] == "po-user"
            assert isinstance(result["po_notes"], str)
            assert isinstance(result["approved_by"], str)


@pytest.mark.asyncio
async def test_get_story_po_approvals(valkey_config):
    """Test get_story_po_approvals retrieves all PO approvals for a story."""
    from datetime import UTC, datetime

    from planning.domain.value_objects.identifiers.story_id import StoryId

    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)

        story_id = StoryId("ST-001")
        approved_at = datetime.now(UTC).isoformat()

        # Mock SCAN results
        scan_results = [
            (0, [b"planning:ceremony:BRC-001:story:ST-001:po_approval"]),
            (0, []),  # Second scan returns empty (cursor=0 means done)
        ]

        approval_data = {
            "po_notes": "Approved in ceremony 1",
            "approved_by": "po-user",
            "approved_at": approved_at,
        }

        with patch('asyncio.to_thread') as mock_to_thread:
            # SCAN returns (cursor, keys) tuple
            # First SCAN call returns (0, [key]) - cursor=0 means done
            # Keys are strings because decode_responses=True
            mock_to_thread.side_effect = [
                (0, ["planning:ceremony:BRC-001:story:ST-001:po_approval"]),  # First SCAN (cursor=0, done)
                approval_data,  # hgetall for first key
            ]

            result = await adapter.get_story_po_approvals(story_id)

            assert len(result) == 1
            assert result[0].story_id == story_id
            assert result[0].ceremony_id.value == "BRC-001"
            assert result[0].po_notes.value == "Approved in ceremony 1"
            assert result[0].approved_by.value == "po-user"


@pytest.mark.asyncio
async def test_get_story_po_approvals_multiple_ceremonies(valkey_config):
    """Test get_story_po_approvals with multiple ceremonies."""
    from datetime import UTC, datetime

    from planning.domain.value_objects.identifiers.story_id import StoryId

    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)

        story_id = StoryId("ST-001")
        approved_at = datetime.now(UTC).isoformat()

        scan_results = [
            (100, [b"planning:ceremony:BRC-001:story:ST-001:po_approval"]),
            (0, [b"planning:ceremony:BRC-002:story:ST-001:po_approval"]),
        ]

        approval_data_1 = {
            "po_notes": "Approved in ceremony 1",
            "approved_by": "po-user-1",
            "approved_at": approved_at,
        }

        approval_data_2 = {
            "po_notes": "Approved in ceremony 2",
            "approved_by": "po-user-2",
            "approved_at": approved_at,
        }

        with patch('asyncio.to_thread') as mock_to_thread:
            # SCAN with cursor=100 continues, cursor=0 stops
            # Keys are strings because decode_responses=True
            mock_to_thread.side_effect = [
                (100, ["planning:ceremony:BRC-001:story:ST-001:po_approval"]),  # First SCAN (cursor=100, continue)
                (0, ["planning:ceremony:BRC-002:story:ST-001:po_approval"]),  # Second SCAN (cursor=0, done)
                approval_data_1,  # hgetall for BRC-001
                approval_data_2,  # hgetall for BRC-002
            ]

            result = await adapter.get_story_po_approvals(story_id)

            assert len(result) == 2
            assert result[0].ceremony_id.value == "BRC-001"
            assert result[1].ceremony_id.value == "BRC-002"


@pytest.mark.asyncio
async def test_get_story_po_approvals_invalid_key_format(valkey_config):
    """Test get_story_po_approvals handles invalid key format."""
    from planning.domain.value_objects.identifiers.story_id import StoryId

    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)

        story_id = StoryId("ST-001")

        scan_results = [
            (0, [b"invalid:key:format"]),  # Invalid key format
        ]

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = [
                (0, ["invalid:key:format"]),  # SCAN (cursor=0, done) - keys are strings
                {},  # hgetall (will be skipped due to invalid key)
            ]

            result = await adapter.get_story_po_approvals(story_id)

            assert len(result) == 0


@pytest.mark.asyncio
async def test_get_story_po_approvals_missing_required_fields(valkey_config):
    """Test get_story_po_approvals skips approvals with missing required fields."""
    from datetime import UTC, datetime

    from planning.domain.value_objects.identifiers.story_id import StoryId

    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)

        story_id = StoryId("ST-001")

        scan_results = [
            (0, [b"planning:ceremony:BRC-001:story:ST-001:po_approval"]),
        ]

        # Missing required fields
        invalid_approval_data = {
            "po_notes": "",  # Empty po_notes (should be skipped)
        }

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = [
                (0, ["planning:ceremony:BRC-001:story:ST-001:po_approval"]),  # SCAN (cursor=0, done) - keys are strings
                invalid_approval_data,  # hgetall
            ]

            result = await adapter.get_story_po_approvals(story_id)

            assert len(result) == 0  # Should skip invalid approval


@pytest.mark.asyncio
async def test_get_story_po_approvals_with_priority_adjustment(valkey_config):
    """Test get_story_po_approvals handles priority_adjustment."""
    from datetime import UTC, datetime

    from planning.domain.value_objects.identifiers.story_id import StoryId

    with patch('valkey.Valkey') as mock_valkey_class:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_valkey_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)

        story_id = StoryId("ST-001")
        approved_at = datetime.now(UTC).isoformat()

        scan_results = [
            (0, [b"planning:ceremony:BRC-001:story:ST-001:po_approval"]),
        ]

        approval_data = {
            "po_notes": "Approved with priority",
            "approved_by": "po-user",
            "approved_at": approved_at,
            "priority_adjustment": "HIGH",
            "po_priority_reason": "Critical",
        }

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = [
                (0, ["planning:ceremony:BRC-001:story:ST-001:po_approval"]),  # SCAN (cursor=0, done) - keys are strings
                approval_data,  # hgetall
            ]

            result = await adapter.get_story_po_approvals(story_id)

            assert len(result) == 1
            assert result[0].priority_adjustment.value == "HIGH"
            assert result[0].po_priority_reason.value == "Critical"
