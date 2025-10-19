"""Tests for MessagingPort interface and DomainEvent."""

from services.orchestrator.domain.ports import DomainEvent, MessagingError


class TestDomainEvent:
    """Test suite for DomainEvent."""
    
    def test_create_event_without_correlation_id(self):
        """Test creating event without correlation ID."""
        event = DomainEvent(
            event_type="test.event",
            payload={"key": "value"},
        )
        
        assert event.event_type == "test.event"
        assert event.payload == {"key": "value"}
        assert event.correlation_id is None
    
    def test_create_event_with_correlation_id(self):
        """Test creating event with correlation ID."""
        event = DomainEvent(
            event_type="test.event",
            payload={"key": "value"},
            correlation_id="corr-123",
        )
        
        assert event.event_type == "test.event"
        assert event.correlation_id == "corr-123"
    
    def test_to_dict_without_correlation_id(self):
        """Test converting event to dict without correlation ID."""
        event = DomainEvent(
            event_type="deliberation.completed",
            payload={"task_id": "task-001", "status": "success"},
        )
        
        result = event.to_dict()
        
        assert result["event_type"] == "deliberation.completed"
        assert result["task_id"] == "task-001"
        assert result["status"] == "success"
        assert "correlation_id" not in result
    
    def test_to_dict_with_correlation_id(self):
        """Test converting event to dict with correlation ID."""
        event = DomainEvent(
            event_type="deliberation.completed",
            payload={"task_id": "task-001"},
            correlation_id="corr-456",
        )
        
        result = event.to_dict()
        
        assert result["event_type"] == "deliberation.completed"
        assert result["correlation_id"] == "corr-456"
    
    def test_to_dict_merges_payload(self):
        """Test that to_dict merges payload into result."""
        event = DomainEvent(
            event_type="test.event",
            payload={"a": 1, "b": 2, "c": 3},
        )
        
        result = event.to_dict()
        
        # All payload keys should be in result
        assert result["a"] == 1
        assert result["b"] == 2
        assert result["c"] == 3
        assert result["event_type"] == "test.event"


class TestMessagingError:
    """Test suite for MessagingError."""
    
    def test_create_error_without_cause(self):
        """Test creating error without underlying cause."""
        error = MessagingError("Connection failed")
        
        assert str(error) == "Connection failed"
        assert error.cause is None
    
    def test_create_error_with_cause(self):
        """Test creating error with underlying cause."""
        original_error = ValueError("Invalid value")
        error = MessagingError("Failed to publish", cause=original_error)
        
        assert str(error) == "Failed to publish"
        assert error.cause == original_error
        assert isinstance(error.cause, ValueError)

