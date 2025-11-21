"""Unit tests for AuditTrailEntry domain entity."""

from datetime import datetime

import pytest
from core.agents_and_tools.agents.domain.entities.collections.audit_trail import AuditTrailEntry


class TestAuditTrailEntryCreation:
    """Test AuditTrailEntry entity creation."""

    def test_create_entry_with_required_fields(self):
        """Test creating entry with required fields."""
        timestamp = datetime.now()
        details = {"tool": "files", "operation": "read_file"}

        entry = AuditTrailEntry(
            timestamp=timestamp,
            event_type="operation_start",
            details=details,
        )

        assert entry.timestamp == timestamp
        assert entry.event_type == "operation_start"
        assert entry.details == details
        assert entry.success is True
        assert entry.error is None

    def test_create_entry_with_all_fields(self):
        """Test creating entry with all fields."""
        timestamp = datetime.now()
        details = {"tool": "files", "operation": "read_file"}

        entry = AuditTrailEntry(
            timestamp=timestamp,
            event_type="operation_end",
            details=details,
            success=False,
            error="File not found",
        )

        assert entry.success is False
        assert entry.error == "File not found"

    def test_create_entry_with_error(self):
        """Test creating entry with error."""
        timestamp = datetime.now()
        details = {"tool": "git", "operation": "commit"}

        entry = AuditTrailEntry(
            timestamp=timestamp,
            event_type="operation_error",
            details=details,
            success=False,
            error="Commit failed: no changes",
        )

        assert entry.success is False
        assert entry.error == "Commit failed: no changes"


class TestAuditTrailEntryImmutability:
    """Test AuditTrailEntry immutability."""

    def test_entry_is_immutable(self):
        """Test entry is frozen (immutable)."""
        timestamp = datetime.now()
        entry = AuditTrailEntry(
            timestamp=timestamp,
            event_type="test",
            details={},
        )

        with pytest.raises(AttributeError):
            entry.event_type = "new_type"  # type: ignore

        with pytest.raises(AttributeError):
            entry.success = False  # type: ignore


class TestAuditTrailEntryEquality:
    """Test AuditTrailEntry equality and comparison."""

    def test_entries_with_same_values_are_equal(self):
        """Test entries with identical values are equal."""
        timestamp = datetime.now()
        details = {"key": "value"}

        entry1 = AuditTrailEntry(
            timestamp=timestamp,
            event_type="test",
            details=details,
        )
        entry2 = AuditTrailEntry(
            timestamp=timestamp,
            event_type="test",
            details=details,
        )

        assert entry1 == entry2

