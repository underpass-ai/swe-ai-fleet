"""Quick coverage for domain_event.py gaps - 2 lines"""

from core.context.domain.domain_event import DomainEvent


def test_get_entity_id_subtask_status_changed():
    """Test get_entity_id for subtask.status_changed event (line 71)."""
    event = DomainEvent.subtask_status_changed("sub-123", "COMPLETED")
    assert event.get_entity_id() == "sub-123"


def test_get_entity_id_unknown_type_fallback():
    """Test get_entity_id fallback for unknown event type (line 79)."""
    event = DomainEvent(
        event_type="unknown.event",
        payload={"node_id": "node-456", "other": "value"}
    )
    assert event.get_entity_id() == "node-456"
