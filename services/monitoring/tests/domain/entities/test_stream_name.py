"""Tests for StreamName value object."""

import pytest
from services.monitoring.domain.entities import StreamName


class TestStreamName:
    """Test suite for StreamName value object."""
    
    def test_creation(self):
        """Test creating a StreamName."""
        name = StreamName(name="orders")
        
        assert name.name == "orders"
        assert str(name) == "orders"
    
    def test_creation_with_hyphens_underscores(self):
        """Test creating with hyphens and underscores."""
        name = StreamName(name="my-stream_v1")
        
        assert name.name == "my-stream_v1"
    
    def test_validate_empty_name(self):
        """Test validation fails with empty name."""
        with pytest.raises(ValueError, match="empty"):
            StreamName(name="")
    
    def test_validate_whitespace_only(self):
        """Test validation fails with whitespace only."""
        with pytest.raises(ValueError, match="empty"):
            StreamName(name="   ")
    
    def test_validate_too_long(self):
        """Test validation fails with name > 255 chars."""
        long_name = "a" * 256
        
        with pytest.raises(ValueError, match="255"):
            StreamName(name=long_name)
    
    def test_validate_invalid_characters(self):
        """Test validation fails with invalid characters."""
        with pytest.raises(ValueError, match="alphanumeric"):
            StreamName(name="my@stream")
    
    def test_validate_invalid_spaces(self):
        """Test validation fails with spaces in name."""
        with pytest.raises(ValueError, match="alphanumeric"):
            StreamName(name="my stream")
    
    def test_immutable(self):
        """Test that StreamName is immutable."""
        name = StreamName(name="orders")
        
        with pytest.raises(AttributeError):
            name.name = "payments"
    
    def test_equals(self):
        """Test equality comparison."""
        name1 = StreamName(name="orders")
        name2 = StreamName(name="orders")
        name3 = StreamName(name="payments")
        
        assert name1.equals(name2) is True
        assert name1.equals(name3) is False
    
    def test_equals_different_type(self):
        """Test equality with different type."""
        name = StreamName(name="orders")
        
        assert name.equals("orders") is False
    
    def test_to_dict(self):
        """Test converting to dict."""
        name = StreamName(name="orders")
        
        result = name.to_dict()
        
        assert result == {"name": "orders"}
    
    def test_create_factory(self):
        """Test factory method."""
        name = StreamName.create("payments")
        
        assert name.name == "payments"
    
    def test_create_factory_validation_fails(self):
        """Test factory fails with invalid params."""
        with pytest.raises(ValueError):
            StreamName.create("")
    
    def test_max_length_valid(self):
        """Test maximum valid length (255 chars)."""
        name = StreamName(name="a" * 255)
        
        assert len(name.name) == 255
    
    def test_hash_equal_values(self):
        """Test that equal StreamNames have same hash."""
        name1 = StreamName(name="orders")
        name2 = StreamName(name="orders")
        
        # Since frozen=True, should be hashable
        assert hash(name1) == hash(name2)
    
    def test_can_use_in_set(self):
        """Test that StreamName can be used in sets."""
        name1 = StreamName(name="orders")
        name2 = StreamName(name="orders")
        name3 = StreamName(name="payments")
        
        stream_set = {name1, name2, name3}
        
        # name1 and name2 are equal, so set has 2 elements
        assert len(stream_set) == 2
