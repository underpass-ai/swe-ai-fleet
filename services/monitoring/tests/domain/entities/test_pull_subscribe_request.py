"""Tests for PullSubscribeRequest entity."""

import pytest
from services.monitoring.domain.entities import PullSubscribeRequest


class TestPullSubscribeRequest:
    """Test suite for PullSubscribeRequest entity."""
    
    def test_creation(self):
        """Test creating a PullSubscribeRequest."""
        req = PullSubscribeRequest(
            subject="orders.>",
            stream="orders",
            durable="consumer-1"
        )
        
        assert req.subject == "orders.>"
        assert req.stream == "orders"
        assert req.durable == "consumer-1"
    
    def test_creation_without_durable(self):
        """Test creating without durable consumer."""
        req = PullSubscribeRequest(
            subject="events.>",
            stream="events"
        )
        
        assert req.subject == "events.>"
        assert req.stream == "events"
        assert req.durable is None
    
    def test_validate_success(self):
        """Test validation success."""
        req = PullSubscribeRequest(
            subject="orders.>",
            stream="orders",
            durable="consumer-1"
        )
        
        # Should not raise
        req.validate()
    
    def test_validate_success_no_durable(self):
        """Test validation success without durable."""
        req = PullSubscribeRequest(
            subject="orders.>",
            stream="orders"
        )
        
        # Should not raise
        req.validate()
    
    def test_validate_empty_subject(self):
        """Test validation fails with empty subject."""
        req = PullSubscribeRequest(
            subject="",
            stream="orders"
        )
        
        with pytest.raises(ValueError, match="subject"):
            req.validate()
    
    def test_validate_empty_stream(self):
        """Test validation fails with empty stream."""
        req = PullSubscribeRequest(
            subject="orders.>",
            stream=""
        )
        
        with pytest.raises(ValueError, match="stream"):
            req.validate()
    
    def test_validate_empty_durable_string(self):
        """Test validation fails with empty durable string."""
        req = PullSubscribeRequest(
            subject="orders.>",
            stream="orders",
            durable=""
        )
        
        with pytest.raises(ValueError, match="durable"):
            req.validate()
    
    def test_to_dict_with_durable(self):
        """Test converting to dict with durable."""
        req = PullSubscribeRequest(
            subject="orders.>",
            stream="orders",
            durable="consumer-1"
        )
        
        result = req.to_dict()
        
        assert result["subject"] == "orders.>"
        assert result["stream"] == "orders"
        assert result["durable"] == "consumer-1"
    
    def test_to_dict_without_durable(self):
        """Test converting to dict without durable."""
        req = PullSubscribeRequest(
            subject="orders.>",
            stream="orders"
        )
        
        result = req.to_dict()
        
        assert result["subject"] == "orders.>"
        assert result["stream"] == "orders"
        assert "durable" not in result
    
    def test_create_factory(self):
        """Test factory method."""
        req = PullSubscribeRequest.create(
            subject="payments.>",
            stream="payments",
            durable="payment-consumer"
        )
        
        assert req.subject == "payments.>"
        assert req.stream == "payments"
        assert req.durable == "payment-consumer"
    
    def test_create_factory_no_durable(self):
        """Test factory without durable."""
        req = PullSubscribeRequest.create(
            subject="events.>",
            stream="events"
        )
        
        assert req.subject == "events.>"
        assert req.durable is None
    
    def test_create_factory_validation_fails(self):
        """Test factory fails with invalid params."""
        with pytest.raises(ValueError):
            PullSubscribeRequest.create(
                subject="",
                stream="orders"
            )
