"""Tests for StreamQuery entity."""

from services.monitoring.domain.entities import StreamQuery


class TestStreamQuery:
    """Test suite for StreamQuery entity."""
    
    def test_creation(self):
        """Test creating a StreamQuery."""
        query = StreamQuery(
            stream_name="orders",
            subject="orders.>",
            limit=50
        )
        
        assert query.stream_name == "orders"
        assert query.subject == "orders.>"
        assert query.limit == 50
    
    def test_get_subject_filter(self):
        """Test getting subject filter."""
        query = StreamQuery(
            stream_name="orders",
            subject="orders.created",
            limit=10
        )
        
        assert query.get_subject_filter() == "orders.created"
    
    def test_validate_success(self):
        """Test validation success."""
        query = StreamQuery(
            stream_name="orders",
            subject="orders.>",
            limit=100
        )
        
        # Should not raise
        query.validate()
    
    def test_validate_empty_stream_name(self):
        """Test validation fails with empty stream."""
        query = StreamQuery(
            stream_name="",
            subject="orders.>",
            limit=10
        )
        
        with pytest.raises(ValueError, match="stream_name"):
            query.validate()
    
    def test_validate_limit_range(self):
        """Test limit validation range."""
        # Too low
        query_low = StreamQuery(
            stream_name="orders",
            subject="orders.>",
            limit=0
        )
        
        with pytest.raises(ValueError, match="limit"):
            query_low.validate()
        
        # Too high
        query_high = StreamQuery(
            stream_name="orders",
            subject="orders.>",
            limit=20000
        )
        
        with pytest.raises(ValueError, match="limit"):
            query_high.validate()
    
    def test_to_dict(self):
        """Test converting to dict."""
        query = StreamQuery(
            stream_name="orders",
            subject="orders.created",
            limit=25
        )
        
        result = query.to_dict()
        
        assert result["stream_name"] == "orders"
        assert result["subject"] == "orders.created"
        assert result["limit"] == 25
    
    def test_create_factory(self):
        """Test factory method."""
        query = StreamQuery.create(
            stream_name="payments",
            subject="payments.>",
            limit=75
        )
        
        assert query.stream_name == "payments"
        assert query.limit == 75


import pytest
