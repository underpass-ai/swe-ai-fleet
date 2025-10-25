"""Tests for SubscribeRequest entity."""

import pytest
from services.monitoring.domain.entities import SubscribeRequest


class TestSubscribeRequest:
    """Test suite for SubscribeRequest entity."""
    
    def test_creation(self):
        """Test creating a SubscribeRequest."""
        req = SubscribeRequest(
            stream_name="orders",
            subject="orders.>"
        )
        
        assert req.stream_name == "orders"
        assert req.subject == "orders.>"
    
    def test_get_subject_filter(self):
        """Test getting subject filter."""
        req = SubscribeRequest(
            stream_name="orders",
            subject="orders.created"
        )
        
        assert req.get_subject_filter() == "orders.created"
    
    def test_validate_success(self):
        """Test validation success."""
        req = SubscribeRequest(
            stream_name="orders",
            subject="orders.>"
        )
        
        # Should not raise
        req.validate()
    
    def test_validate_empty_stream_name(self):
        """Test validation fails with empty stream."""
        req = SubscribeRequest(
            stream_name="",
            subject="orders.>"
        )
        
        with pytest.raises(ValueError, match="stream_name"):
            req.validate()
    
    def test_validate_empty_subject(self):
        """Test validation fails with empty subject."""
        req = SubscribeRequest(
            stream_name="orders",
            subject=""
        )
        
        with pytest.raises(ValueError, match="subject"):
            req.validate()
    
    def test_to_dict(self):
        """Test converting to dict."""
        req = SubscribeRequest(
            stream_name="orders",
            subject="orders.shipped"
        )
        
        result = req.to_dict()
        
        assert result["stream_name"] == "orders"
        assert result["subject"] == "orders.shipped"
    
    def test_create_factory(self):
        """Test factory method."""
        req = SubscribeRequest.create(
            stream_name="payments",
            subject="payments.completed"
        )
        
        assert req.stream_name == "payments"
        assert req.subject == "payments.completed"
