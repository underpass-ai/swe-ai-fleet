"""Tests for FetchRequest entity."""

import pytest
from services.monitoring.domain.entities import FetchRequest


class TestFetchRequest:
    """Test suite for FetchRequest entity."""
    
    def test_creation(self):
        """Test creating a FetchRequest."""
        req = FetchRequest(limit=10, timeout=30)
        
        assert req.limit == 10
        assert req.timeout == 30
    
    def test_validate_success(self):
        """Test validation success."""
        req = FetchRequest(limit=5, timeout=10)
        
        # Should not raise
        req.validate()
    
    def test_validate_limit_too_low(self):
        """Test validation fails with limit < 1."""
        req = FetchRequest(limit=0, timeout=5)
        
        with pytest.raises(ValueError, match="limit"):
            req.validate()
    
    def test_validate_limit_too_high(self):
        """Test validation fails with limit > 10000."""
        req = FetchRequest(limit=10001, timeout=5)
        
        with pytest.raises(ValueError, match="limit"):
            req.validate()
    
    def test_validate_timeout_too_low(self):
        """Test validation fails with timeout < 1."""
        req = FetchRequest(limit=5, timeout=0)
        
        with pytest.raises(ValueError, match="timeout"):
            req.validate()
    
    def test_validate_timeout_too_high(self):
        """Test validation fails with timeout > 300."""
        req = FetchRequest(limit=5, timeout=301)
        
        with pytest.raises(ValueError, match="timeout"):
            req.validate()
    
    def test_to_dict(self):
        """Test converting to dict."""
        req = FetchRequest(limit=25, timeout=60)
        
        result = req.to_dict()
        
        assert result["limit"] == 25
        assert result["timeout"] == 60
    
    def test_create_factory(self):
        """Test factory method."""
        req = FetchRequest.create(limit=50, timeout=120)
        
        assert req.limit == 50
        assert req.timeout == 120
    
    def test_create_factory_validation_fails(self):
        """Test factory fails with invalid params."""
        with pytest.raises(ValueError):
            FetchRequest.create(limit=0, timeout=5)
    
    def test_default_monitoring(self):
        """Test default monitoring preset."""
        req = FetchRequest.default_monitoring()
        
        assert req.limit == 1
        assert req.timeout == 5
    
    def test_min_valid_values(self):
        """Test minimum valid values."""
        req = FetchRequest.create(limit=1, timeout=1)
        
        assert req.limit == 1
        assert req.timeout == 1
    
    def test_max_valid_values(self):
        """Test maximum valid values."""
        req = FetchRequest.create(limit=10000, timeout=300)
        
        assert req.limit == 10000
        assert req.timeout == 300
