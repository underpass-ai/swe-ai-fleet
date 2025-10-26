"""Extended tests for StreamInfo entity edge cases."""

from services.monitoring.domain.entities import StreamInfo


class TestStreamInfoEdgeCases:
    """Extended test suite for StreamInfo edge cases."""
    
    def test_creation_with_multiple_subjects(self):
        """Test with multiple subjects."""
        info = StreamInfo(
            name="multi-stream",
            subjects=["orders.>", "payments.>", "shipping.>"],
            messages=500,
            bytes=250000,
            first_seq=1,
            last_seq=500,
            consumer_count=5
        )
        
        assert len(info.subjects) == 3
        assert "orders.>" in info.subjects
    
    def test_get_size_mb_large_stream(self):
        """Test size calculation for large streams."""
        info = StreamInfo(
            name="large",
            subjects=["events.>"],
            messages=1000000,
            bytes=1024 * 1024 * 100,  # 100 MB
            first_seq=1,
            last_seq=1000000,
            consumer_count=10
        )
        
        assert abs(info.get_size_mb() - 100.0) < 0.01
    
    def test_get_size_mb_bytes(self):
        """Test size calculation in bytes."""
        info = StreamInfo(
            name="small",
            subjects=["events.>"],
            messages=10,
            bytes=512,  # 512 bytes
            first_seq=1,
            last_seq=10,
            consumer_count=1
        )
        
        assert info.get_size_mb() < 0.001  # Less than 1 KB
    
    def test_empty_with_non_zero_sequence(self):
        """Test stream with sequences but no messages."""
        info = StreamInfo(
            name="empty",
            subjects=[],
            messages=0,
            bytes=0,
            first_seq=100,  # Had messages before
            last_seq=100,
            consumer_count=0
        )
        
        assert info.is_empty() is True
    
    def test_single_message_stream(self):
        """Test stream with single message."""
        info = StreamInfo(
            name="single",
            subjects=["event"],
            messages=1,
            bytes=256,
            first_seq=1,
            last_seq=1,
            consumer_count=1
        )
        
        assert info.is_empty() is False
        assert info.messages == 1
    
    def test_high_consumer_count(self):
        """Test stream with many consumers."""
        info = StreamInfo(
            name="popular",
            subjects=["broadcast.>"],
            messages=10000,
            bytes=5000000,
            first_seq=1,
            last_seq=10000,
            consumer_count=50
        )
        
        assert info.consumer_count == 50
    
    def test_to_dict_preserves_all_fields(self):
        """Test that to_dict preserves all fields exactly."""
        original_data = {
            "name": "test-stream",
            "subjects": ["test.a", "test.b"],
            "messages": 42,
            "bytes": 2048,
            "first_seq": 5,
            "last_seq": 47,
            "consumer_count": 3
        }
        
        info = StreamInfo(**original_data)
        result = info.to_dict()
        
        for key, value in original_data.items():
            assert result[key] == value
