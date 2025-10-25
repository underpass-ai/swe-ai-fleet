"""Tests for MessagesCollection entity."""

from services.monitoring.domain.entities import MessagesCollection, StreamMessage


class TestMessagesCollection:
    """Test suite for MessagesCollection entity."""
    
    def test_creation_empty(self):
        """Test creating an empty collection."""
        collection = MessagesCollection()
        
        assert collection.messages == []
        assert collection.count() == 0
        assert collection.is_empty() is True
    
    def test_add_message(self):
        """Test adding messages to collection."""
        collection = MessagesCollection()
        
        msg1 = StreamMessage(
            subject="events.order",
            data={"order_id": "1"},
            sequence=1,
            timestamp="2025-10-25T10:00:00Z"
        )
        msg2 = StreamMessage(
            subject="events.order",
            data={"order_id": "2"},
            sequence=2,
            timestamp="2025-10-25T10:01:00Z"
        )
        
        collection.add(msg1)
        collection.add(msg2)
        
        assert collection.count() == 2
        assert collection.is_empty() is False
        assert collection.messages[0].data["order_id"] == "1"
        assert collection.messages[1].data["order_id"] == "2"
    
    def test_get_latest(self):
        """Test getting latest message."""
        collection = MessagesCollection()
        
        msg1 = StreamMessage(
            subject="events.order",
            data={"order_id": "1"},
            sequence=1,
            timestamp="2025-10-25T10:00:00Z"
        )
        msg2 = StreamMessage(
            subject="events.order",
            data={"order_id": "2"},
            sequence=2,
            timestamp="2025-10-25T10:01:00Z"
        )
        
        collection.add(msg1)
        collection.add(msg2)
        
        latest = collection.get_latest()
        
        assert latest.data["order_id"] == "2"
    
    def test_filter_by_subject(self):
        """Test filtering by subject."""
        collection = MessagesCollection()
        
        msg1 = StreamMessage(
            subject="events.order",
            data={},
            sequence=1,
            timestamp="2025-10-25T10:00:00Z"
        )
        msg2 = StreamMessage(
            subject="events.payment",
            data={},
            sequence=2,
            timestamp="2025-10-25T10:01:00Z"
        )
        msg3 = StreamMessage(
            subject="events.order",
            data={},
            sequence=3,
            timestamp="2025-10-25T10:02:00Z"
        )
        
        collection.add(msg1)
        collection.add(msg2)
        collection.add(msg3)
        
        orders = collection.filter_by_subject("events.order")
        
        assert orders.count() == 2
        assert orders.messages[0].subject == "events.order"
        assert orders.messages[1].subject == "events.order"
    
    def test_to_list(self):
        """Test converting to list of dicts."""
        collection = MessagesCollection()
        
        msg = StreamMessage(
            subject="events.order",
            data={"order_id": "1"},
            sequence=1,
            timestamp="2025-10-25T10:00:00Z"
        )
        collection.add(msg)
        
        result = collection.to_list()
        
        assert len(result) == 1
        assert result[0]["subject"] == "events.order"
        assert result[0]["data"]["order_id"] == "1"
    
    def test_create_factory(self):
        """Test factory method."""
        msg1 = StreamMessage(
            subject="events.test",
            data={"id": 1},
            sequence=1,
            timestamp="2025-10-25T10:00:00Z"
        )
        
        collection = MessagesCollection.create(messages=[msg1])
        
        assert collection.count() == 1
        assert collection.messages[0].data["id"] == 1
