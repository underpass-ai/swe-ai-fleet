"""Tests for StreamMessage entity."""

from services.monitoring.domain.entities import StreamMessage


class TestStreamMessage:
    """Test suite for StreamMessage entity."""
    
    def test_creation(self):
        """Test creating a StreamMessage."""
        msg = StreamMessage(
            subject="events.order",
            data={"order_id": "123", "amount": 99.99},
            sequence=1,
            timestamp="2025-10-25T10:30:00Z"
        )
        
        assert msg.subject == "events.order"
        assert msg.data == {"order_id": "123", "amount": 99.99}
        assert msg.sequence == 1
        assert msg.timestamp == "2025-10-25T10:30:00Z"
    
    def test_get_event_type(self):
        """Test extracting event type from subject."""
        msg = StreamMessage(
            subject="events.order.created",
            data={},
            sequence=1,
            timestamp="2025-10-25T10:30:00Z"
        )
        
        assert msg.get_event_type() == "events.order.created"
    
    def test_to_dict(self):
        """Test converting to dict."""
        msg = StreamMessage(
            subject="events.order",
            data={"order_id": "123"},
            sequence=5,
            timestamp="2025-10-25T10:30:00Z"
        )
        
        result = msg.to_dict()
        
        assert result["subject"] == "events.order"
        assert result["data"] == {"order_id": "123"}
        assert result["sequence"] == 5
        assert result["timestamp"] == "2025-10-25T10:30:00Z"
    
    def test_create_factory(self):
        """Test factory method."""
        msg = StreamMessage.create(
            subject="task.completed",
            data={"task_id": "789", "status": "success"},
            sequence=42,
            timestamp="2025-10-25T11:00:00Z"
        )
        
        assert msg.subject == "task.completed"
        assert msg.data["task_id"] == "789"
        assert msg.sequence == 42
