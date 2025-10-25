"""Tests for PushSubscribeRequest entity."""

import pytest
from services.monitoring.domain.entities import PushSubscribeRequest


class TestPushSubscribeRequest:
    """Test suite for PushSubscribeRequest entity."""
    
    def test_creation(self):
        """Test creating a PushSubscribeRequest."""
        req = PushSubscribeRequest(
            subject="orders.>",
            stream="orders",
            ordered_consumer=True
        )
        
        assert req.subject == "orders.>"
        assert req.stream == "orders"
        assert req.ordered_consumer is True
    
    def test_creation_defaults(self):
        """Test creating with default values."""
        req = PushSubscribeRequest(subject="events.>")
        
        assert req.subject == "events.>"
        assert req.stream is None
        assert req.ordered_consumer is False
    
    def test_validate_success(self):
        """Test validation success."""
        req = PushSubscribeRequest(
            subject="orders.>",
            stream="orders",
            ordered_consumer=True
        )
        
        # Should not raise
        req.validate()
    
    def test_validate_empty_subject(self):
        """Test validation fails with empty subject."""
        req = PushSubscribeRequest(subject="")
        
        with pytest.raises(ValueError, match="subject"):
            req.validate()
    
    def test_validate_empty_stream_string(self):
        """Test validation fails with empty stream string."""
        req = PushSubscribeRequest(
            subject="events.>",
            stream=""
        )
        
        with pytest.raises(ValueError, match="stream"):
            req.validate()
    
    def test_validate_none_stream_ok(self):
        """Test validation allows None stream."""
        req = PushSubscribeRequest(
            subject="events.>",
            stream=None
        )
        
        # Should not raise
        req.validate()
    
    def test_validate_ordered_consumer_not_bool(self):
        """Test validation fails if ordered_consumer not bool."""
        req = PushSubscribeRequest(
            subject="events.>",
            ordered_consumer="true"  # String instead of bool
        )
        
        with pytest.raises(ValueError, match="ordered_consumer"):
            req.validate()
    
    def test_to_dict_full(self):
        """Test converting to dict with all fields."""
        req = PushSubscribeRequest(
            subject="orders.>",
            stream="orders",
            ordered_consumer=True
        )
        
        result = req.to_dict()
        
        assert result["subject"] == "orders.>"
        assert result["stream"] == "orders"
        assert result["ordered_consumer"] is True
    
    def test_to_dict_minimal(self):
        """Test converting to dict without optional stream."""
        req = PushSubscribeRequest(
            subject="events.>",
            ordered_consumer=False
        )
        
        result = req.to_dict()
        
        assert result["subject"] == "events.>"
        assert "stream" not in result
        assert result["ordered_consumer"] is False
    
    def test_create_factory(self):
        """Test factory method."""
        req = PushSubscribeRequest.create(
            subject="payments.>",
            stream="payments",
            ordered_consumer=True
        )
        
        assert req.subject == "payments.>"
        assert req.stream == "payments"
        assert req.ordered_consumer is True
    
    def test_create_factory_validation_fails(self):
        """Test factory fails with invalid params."""
        with pytest.raises(ValueError):
            PushSubscribeRequest.create(
                subject="",
                stream="orders"
            )
