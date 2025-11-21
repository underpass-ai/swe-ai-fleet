"""Unit tests for AuditTrails collection."""

from datetime import datetime

from core.agents_and_tools.agents.domain.entities.collections.audit_trail import AuditTrailEntry
from core.agents_and_tools.agents.domain.entities.collections.audit_trails import AuditTrails


class TestAuditTrailsCreation:
    """Test AuditTrails collection creation."""

    def test_create_empty_audit_trails(self):
        """Test creating empty audit trails collection."""
        trails = AuditTrails()

        assert trails.entries == []
        assert trails.count() == 0

    def test_create_audit_trails_with_entries(self):
        """Test creating audit trails collection with initial entries."""
        timestamp = datetime.now()
        entry1 = AuditTrailEntry(
            timestamp=timestamp,
            event_type="operation_start",
            details={},
        )
        entry2 = AuditTrailEntry(
            timestamp=timestamp,
            event_type="operation_end",
            details={},
        )

        trails = AuditTrails(entries=[entry1, entry2])

        assert trails.count() == 2
        assert len(trails.entries) == 2


class TestAuditTrailsAdd:
    """Test AuditTrails.add() method."""

    def test_add_successful_entry(self):
        """Test adding successful entry."""
        trails = AuditTrails()

        trails.add(
            event_type="operation_start",
            details={"tool": "files", "operation": "read_file"},
            success=True,
        )

        assert trails.count() == 1
        entry = trails.entries[0]
        assert entry.event_type == "operation_start"
        assert entry.details == {"tool": "files", "operation": "read_file"}
        assert entry.success is True
        assert entry.error is None

    def test_add_failed_entry(self):
        """Test adding failed entry."""
        trails = AuditTrails()

        trails.add(
            event_type="operation_error",
            details={"tool": "files", "operation": "read_file"},
            success=False,
            error="File not found",
        )

        entry = trails.entries[0]
        assert entry.success is False
        assert entry.error == "File not found"

    def test_add_entry_creates_timestamp(self):
        """Test that add() creates a timestamp for the entry."""
        trails = AuditTrails()
        before = datetime.now()

        trails.add(event_type="test", details={})

        after = datetime.now()
        entry = trails.entries[0]
        assert before <= entry.timestamp <= after


class TestAuditTrailsGetAll:
    """Test AuditTrails.get_all() method."""

    def test_get_all_returns_all_entries(self):
        """Test get_all returns all entries."""
        trails = AuditTrails()
        trails.add(event_type="event1", details={})
        trails.add(event_type="event2", details={})

        all_entries = trails.get_all()

        assert len(all_entries) == 2
        assert all_entries == trails.entries


class TestAuditTrailsGetByEventType:
    """Test AuditTrails.get_by_event_type() method."""

    def test_get_by_event_type_returns_matching_entries(self):
        """Test get_by_event_type returns entries with specific type."""
        trails = AuditTrails()
        trails.add(event_type="operation_start", details={})
        trails.add(event_type="operation_end", details={})
        trails.add(event_type="operation_start", details={})

        start_entries = trails.get_by_event_type("operation_start")

        assert len(start_entries) == 2
        assert all(entry.event_type == "operation_start" for entry in start_entries)

    def test_get_by_event_type_returns_empty_list_when_no_matches(self):
        """Test get_by_event_type returns empty list when no matches."""
        trails = AuditTrails()
        trails.add(event_type="operation_start", details={})

        end_entries = trails.get_by_event_type("operation_end")

        assert end_entries == []


class TestAuditTrailsGetErrors:
    """Test AuditTrails.get_errors() method."""

    def test_get_errors_returns_only_failed_entries(self):
        """Test get_errors returns only failed entries."""
        trails = AuditTrails()
        trails.add(event_type="event1", details={}, success=True)
        trails.add(event_type="event2", details={}, success=False, error="Error 1")
        trails.add(event_type="event3", details={}, success=True)
        trails.add(event_type="event4", details={}, success=False, error="Error 2")

        errors = trails.get_errors()

        assert len(errors) == 2
        assert all(not entry.success for entry in errors)

    def test_get_errors_returns_empty_list_when_no_errors(self):
        """Test get_errors returns empty list when no errors."""
        trails = AuditTrails()
        trails.add(event_type="event1", details={}, success=True)
        trails.add(event_type="event2", details={}, success=True)

        errors = trails.get_errors()

        assert errors == []


class TestAuditTrailsCount:
    """Test AuditTrails.count() method."""

    def test_count_returns_zero_for_empty_collection(self):
        """Test count returns zero for empty collection."""
        trails = AuditTrails()

        assert trails.count() == 0

    def test_count_returns_correct_number(self):
        """Test count returns correct number of entries."""
        trails = AuditTrails()

        trails.add(event_type="event1", details={})
        assert trails.count() == 1

        trails.add(event_type="event2", details={})
        assert trails.count() == 2

