"""Tests for AsyncioExecutor."""

import asyncio

import pytest
from core.ray_jobs.infrastructure.adapters import AsyncioExecutor


class TestAsyncioExecutor:
    """Tests for AsyncioExecutor."""
    
    def test_run_simple_coroutine(self):
        """Test executing a simple coroutine."""
        # Arrange
        async def simple_coro():
            return "test result"
        
        executor = AsyncioExecutor()
        
        # Act
        result = executor.run(simple_coro())
        
        # Assert
        assert result == "test result"
    
    def test_run_coroutine_with_await(self):
        """Test executing a coroutine that awaits."""
        # Arrange
        async def async_operation():
            await asyncio.sleep(0.01)
            return 42
        
        executor = AsyncioExecutor()
        
        # Act
        result = executor.run(async_operation())
        
        # Assert
        assert result == 42
    
    def test_run_coroutine_with_exception(self):
        """Test that exceptions are propagated."""
        # Arrange
        async def failing_coro():
            raise ValueError("Test error")
        
        executor = AsyncioExecutor()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Test error"):
            executor.run(failing_coro())
    
    def test_run_coroutine_with_complex_return(self):
        """Test executing a coroutine that returns complex data."""
        # Arrange
        async def complex_coro():
            return {
                "status": "success",
                "data": [1, 2, 3],
                "nested": {"key": "value"},
            }
        
        executor = AsyncioExecutor()
        
        # Act
        result = executor.run(complex_coro())
        
        # Assert
        assert result["status"] == "success"
        assert result["data"] == [1, 2, 3]
        assert result["nested"]["key"] == "value"
    
    def test_run_multiple_times(self):
        """Test that executor can be used multiple times."""
        # Arrange
        async def counter_coro(value):
            return value * 2
        
        executor = AsyncioExecutor()
        
        # Act
        result1 = executor.run(counter_coro(5))
        result2 = executor.run(counter_coro(10))
        result3 = executor.run(counter_coro(3))
        
        # Assert
        assert result1 == 10
        assert result2 == 20
        assert result3 == 6
    
    def test_run_coroutine_with_multiple_awaits(self):
        """Test executing a coroutine with multiple await points."""
        # Arrange
        async def multi_await_coro():
            result = 0
            for i in range(3):
                await asyncio.sleep(0.001)
                result += i
            return result
        
        executor = AsyncioExecutor()
        
        # Act
        result = executor.run(multi_await_coro())
        
        # Assert
        assert result == 3  # 0 + 1 + 2

