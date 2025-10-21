"""Tests for DeliberateUseCase."""

import pytest

from services.orchestrator.application import DeliberateUseCase
from services.orchestrator.domain.entities import OrchestratorStatistics


class MockCouncil:
    """Mock council for testing."""
    
    def __init__(self, results=None):
        self.results = results or [{"proposal": "test"}]
        self.execute_called = False
    
    def execute(self, task_description, constraints):
        """Mock execute method."""
        self.execute_called = True
        self.task_description = task_description
        self.constraints = constraints
        return self.results


class MockConstraints:
    """Mock constraints for testing."""
    pass


class TestDeliberateUseCase:
    """Test suite for DeliberateUseCase."""
    
    def test_execute_success(self):
        """Test successful deliberation execution."""
        stats = OrchestratorStatistics()
        council = MockCouncil(results=[{"proposal": "solution"}])
        use_case = DeliberateUseCase(stats=stats)
        
        result = use_case.execute(
            council=council,
            role="Coder",
            task_description="Fix bug",
            constraints=MockConstraints()
        )
        
        assert result.results == [{"proposal": "solution"}]
        assert result.duration_ms >= 0
        assert result.stats == stats
        assert council.execute_called is True
    
    def test_execute_updates_stats(self):
        """Test that execution updates statistics."""
        stats = OrchestratorStatistics()
        council = MockCouncil()
        use_case = DeliberateUseCase(stats=stats)
        
        initial_count = stats.total_deliberations
        
        use_case.execute(
            council=council,
            role="Coder",
            task_description="Fix bug",
            constraints=MockConstraints()
        )
        
        assert stats.total_deliberations == initial_count + 1
        assert "Coder" in stats.role_counts
    
    def test_execute_none_council_raises(self):
        """Test that None council raises RuntimeError."""
        stats = OrchestratorStatistics()
        use_case = DeliberateUseCase(stats=stats)
        
        with pytest.raises(RuntimeError, match="cannot be None"):
            use_case.execute(
                council=None,
                role="Coder",
                task_description="Fix bug",
                constraints=MockConstraints()
            )
    
    def test_execute_empty_role_raises(self):
        """Test that empty role raises ValueError."""
        stats = OrchestratorStatistics()
        council = MockCouncil()
        use_case = DeliberateUseCase(stats=stats)
        
        with pytest.raises(ValueError, match="Role cannot be empty"):
            use_case.execute(
                council=council,
                role="",
                task_description="Fix bug",
                constraints=MockConstraints()
            )
    
    def test_execute_empty_task_description_raises(self):
        """Test that empty task description raises ValueError."""
        stats = OrchestratorStatistics()
        council = MockCouncil()
        use_case = DeliberateUseCase(stats=stats)
        
        with pytest.raises(ValueError, match="Task description cannot be empty"):
            use_case.execute(
                council=council,
                role="Coder",
                task_description="   ",
                constraints=MockConstraints()
            )
    
    def test_execute_measures_duration(self):
        """Test that execution measures duration."""
        stats = OrchestratorStatistics()
        council = MockCouncil()
        use_case = DeliberateUseCase(stats=stats)
        
        result = use_case.execute(
            council=council,
            role="Coder",
            task_description="Fix bug",
            constraints=MockConstraints()
        )
        
        assert result.duration_ms >= 0  # Can be 0 if very fast
        assert isinstance(result.duration_ms, int)

