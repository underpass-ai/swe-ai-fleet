"""Tests for OrchestratorStatistics entity."""

from services.orchestrator.domain.entities import OrchestratorStatistics


class TestOrchestratorStatistics:
    """Test suite for OrchestratorStatistics entity."""
    
    def test_creation(self):
        """Test creating statistics entity."""
        stats = OrchestratorStatistics()
        
        assert stats.total_deliberations == 0
        assert stats.total_orchestrations == 0
        assert stats.average_duration_ms == 0.0
        assert len(stats.role_counts) == 0
    
    def test_increment_deliberation(self):
        """Test incrementing deliberation count."""
        stats = OrchestratorStatistics()
        
        stats.increment_deliberation("Coder", 1000)
        
        assert stats.total_deliberations == 1
        assert stats.role_counts["Coder"] == 1
        assert stats.average_duration_ms == 1000.0
    
    def test_increment_deliberation_multiple(self):
        """Test incrementing deliberation multiple times."""
        stats = OrchestratorStatistics()
        
        stats.increment_deliberation("Coder", 1000)
        stats.increment_deliberation("Coder", 2000)
        stats.increment_deliberation("Reviewer", 1500)
        
        assert stats.total_deliberations == 3
        assert stats.role_counts["Coder"] == 2
        assert stats.role_counts["Reviewer"] == 1
        assert stats.average_duration_ms == 1500.0  # (1000 + 2000 + 1500) / 3
    
    def test_increment_orchestration(self):
        """Test incrementing orchestration count."""
        stats = OrchestratorStatistics()
        
        stats.increment_orchestration(2000)
        
        assert stats.total_orchestrations == 1
        assert stats.average_duration_ms == 2000.0
    
    def test_combined_deliberation_and_orchestration(self):
        """Test combined stats for deliberations and orchestrations."""
        stats = OrchestratorStatistics()
        
        stats.increment_deliberation("Coder", 1000)
        stats.increment_orchestration(3000)
        
        assert stats.total_deliberations == 1
        assert stats.total_orchestrations == 1
        assert stats.average_duration_ms == 2000.0  # (1000 + 3000) / 2
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        stats = OrchestratorStatistics()
        stats.increment_deliberation("Coder", 1000)
        stats.increment_orchestration(2000)
        
        result = stats.to_dict()
        
        assert result["total_deliberations"] == 1
        assert result["total_orchestrations"] == 1
        assert result["average_duration_ms"] == 1500.0
        assert result["role_counts"]["Coder"] == 1

