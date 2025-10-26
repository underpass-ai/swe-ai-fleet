"""Tests for StreamInfo entity."""

from services.monitoring.domain.entities import StreamInfo


class TestStreamInfo:
    """Test suite for StreamInfo entity."""
    
    def test_creation(self):
        """Test creating a StreamInfo."""
        info = StreamInfo(
            name="test-stream",
            subjects=["events.>"],
            messages=100,
            bytes=50000,
            first_seq=1,
            last_seq=100,
            consumer_count=2
        )
        
        assert info.name == "test-stream"
        assert info.subjects == ["events.>"]
        assert info.messages == 100
        assert info.bytes == 50000
        assert info.first_seq == 1
        assert info.last_seq == 100
        assert info.consumer_count == 2
    
    def test_is_empty(self):
        """Test is_empty method."""
        # Empty stream
        empty = StreamInfo(
            name="empty",
            subjects=[],
            messages=0,
            bytes=0,
            first_seq=0,
            last_seq=0,
            consumer_count=0
        )
        assert empty.is_empty() is True
        
        # Non-empty stream
        full = StreamInfo(
            name="full",
            subjects=["events.>"],
            messages=100,
            bytes=50000,
            first_seq=1,
            last_seq=100,
            consumer_count=2
        )
        assert full.is_empty() is False
    
    def test_get_size_mb(self):
        """Test size calculation in MB."""
        info = StreamInfo(
            name="test",
            subjects=["events.>"],
            messages=100,
            bytes=1048576,  # 1 MB
            first_seq=1,
            last_seq=100,
            consumer_count=1
        )
        
        assert abs(info.get_size_mb() - 1.0) < 0.01
    
    def test_to_dict(self):
        """Test converting to dict."""
        info = StreamInfo(
            name="test-stream",
            subjects=["events.>"],
            messages=100,
            bytes=50000,
            first_seq=1,
            last_seq=100,
            consumer_count=2
        )
        
        result = info.to_dict()
        
        assert result["name"] == "test-stream"
        assert result["subjects"] == ["events.>"]
        assert result["messages"] == 100
        assert result["bytes"] == 50000
        assert result["first_seq"] == 1
        assert result["last_seq"] == 100
        assert result["consumer_count"] == 2
    
    def test_create_factory(self):
        """Test factory method."""
        info = StreamInfo.create(
            name="factory-stream",
            subjects=["orders.>"],
            messages=50,
            bytes=25000,
            first_seq=1,
            last_seq=50,
            consumer_count=1
        )
        
        assert info.name == "factory-stream"
        assert info.subjects == ["orders.>"]
        assert info.messages == 50
