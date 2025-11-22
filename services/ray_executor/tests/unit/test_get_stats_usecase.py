"""Unit tests for GetStatsUseCase."""

import time

import pytest

from services.ray_executor.application.usecases import GetStatsUseCase


@pytest.mark.asyncio
async def test_get_stats_empty():
    """Test retrieving stats with no deliberations."""
    # Arrange
    stats = {
        'total_deliberations': 0,
        'active_deliberations': 0,
        'completed_deliberations': 0,
        'failed_deliberations': 0,
        'execution_times': []
    }
    start_time = time.time()

    use_case = GetStatsUseCase(
        stats_tracker=stats,
        start_time=start_time,
    )

    # Act
    execution_stats, uptime = await use_case.execute()

    # Assert
    assert execution_stats.total_deliberations == 0
    assert execution_stats.active_deliberations == 0
    assert execution_stats.completed_deliberations == 0
    assert execution_stats.failed_deliberations == 0
    assert execution_stats.average_execution_time_ms == pytest.approx(0.0)
    assert uptime >= 0


@pytest.mark.asyncio
async def test_get_stats_with_execution_times():
    """Test stats calculation with execution times."""
    # Arrange
    stats = {
        'total_deliberations': 5,
        'active_deliberations': 1,
        'completed_deliberations': 3,
        'failed_deliberations': 1,
        'execution_times': [1.5, 2.0, 2.5]  # seconds
    }
    start_time = time.time() - 3600  # 1 hour ago

    use_case = GetStatsUseCase(
        stats_tracker=stats,
        start_time=start_time,
    )

    # Act
    execution_stats, uptime = await use_case.execute()

    # Assert
    assert execution_stats.total_deliberations == 5
    assert execution_stats.active_deliberations == 1
    assert execution_stats.completed_deliberations == 3
    assert execution_stats.failed_deliberations == 1

    # Average of [1.5, 2.0, 2.5] = 2.0 seconds = 2000 ms
    assert execution_stats.average_execution_time_ms == pytest.approx(2000.0)

    # Uptime should be approximately 3600 seconds
    assert 3599 <= uptime <= 3601


@pytest.mark.asyncio
async def test_get_stats_validates_negative_values():
    """Test that ExecutionStats validates negative values."""
    # Arrange
    from services.ray_executor.domain.entities import ExecutionStats

    # Act & Assert
    with pytest.raises(ValueError, match="total_deliberations cannot be negative"):
        ExecutionStats(
            total_deliberations=-1,
            active_deliberations=0,
            completed_deliberations=0,
            failed_deliberations=0,
            average_execution_time_ms=0.0,
        )

