"""Tests for DurableConsumer entity."""

import pytest
from services.monitoring.domain.entities import DurableConsumer


class TestDurableConsumer:
    """Test suite for DurableConsumer entity."""
    
    def test_creation(self):
        """Test creating a DurableConsumer."""
        consumer = DurableConsumer(
            subject="orders.>",
            stream_name="orders",
            durable_name="consumer-1"
        )
        
        assert consumer.subject == "orders.>"
        assert consumer.stream_name == "orders"
        assert consumer.durable_name == "consumer-1"
    
    def test_get_subject_filter(self):
        """Test getting subject filter."""
        consumer = DurableConsumer(
            subject="orders.created",
            stream_name="orders",
            durable_name="consumer-1"
        )
        
        assert consumer.get_subject_filter() == "orders.created"
    
    def test_get_consumer_name(self):
        """Test getting consumer name."""
        consumer = DurableConsumer(
            subject="orders.>",
            stream_name="orders",
            durable_name="monitoring-consumer"
        )
        
        assert consumer.get_consumer_name() == "monitoring-consumer"
    
    def test_validate_success(self):
        """Test validation success."""
        consumer = DurableConsumer(
            subject="orders.>",
            stream_name="orders",
            durable_name="consumer-1"
        )
        
        # Should not raise
        consumer.validate()
    
    def test_validate_empty_subject(self):
        """Test validation fails with empty subject."""
        consumer = DurableConsumer(
            subject="",
            stream_name="orders",
            durable_name="consumer-1"
        )
        
        with pytest.raises(ValueError, match="subject"):
            consumer.validate()
    
    def test_validate_empty_stream_name(self):
        """Test validation fails with empty stream."""
        consumer = DurableConsumer(
            subject="orders.>",
            stream_name="",
            durable_name="consumer-1"
        )
        
        with pytest.raises(ValueError, match="stream_name"):
            consumer.validate()
    
    def test_validate_empty_durable_name(self):
        """Test validation fails with empty durable name."""
        consumer = DurableConsumer(
            subject="orders.>",
            stream_name="orders",
            durable_name=""
        )
        
        with pytest.raises(ValueError, match="durable_name"):
            consumer.validate()
    
    def test_to_dict(self):
        """Test converting to dict."""
        consumer = DurableConsumer(
            subject="orders.>",
            stream_name="orders",
            durable_name="consumer-1"
        )
        
        result = consumer.to_dict()
        
        assert result["subject"] == "orders.>"
        assert result["stream_name"] == "orders"
        assert result["durable_name"] == "consumer-1"
    
    def test_for_monitoring_factory(self):
        """Test for_monitoring factory method."""
        consumer = DurableConsumer.for_monitoring(
            stream_name="orders",
            subject="orders.>"
        )
        
        assert consumer.stream_name == "orders"
        assert consumer.subject == "orders.>"
        assert "monitoring" in consumer.durable_name
    
    def test_create_factory(self):
        """Test create factory method."""
        consumer = DurableConsumer.create(
            subject="payments.>",
            stream_name="payments",
            durable_name="payment-consumer"
        )
        
        assert consumer.subject == "payments.>"
        assert consumer.stream_name == "payments"
        assert consumer.durable_name == "payment-consumer"
