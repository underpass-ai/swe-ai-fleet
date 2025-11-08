"""Unit tests for GetActiveJobsUseCase."""

import time

import pytest
from services.ray_executor.application.usecases.get_active_jobs_usecase import GetActiveJobsUseCase
from services.ray_executor.domain.entities import JobInfo

# =============================================================================
# Constructor Tests
# =============================================================================

class TestGetActiveJobsUseCaseConstructor:
    """Test use case constructor and dependency injection."""

    def test_creates_with_registry(self):
        """Should create use case with deliberations registry."""
        deliberations_registry = {}

        use_case = GetActiveJobsUseCase(
            deliberations_registry=deliberations_registry,
        )

        assert use_case._deliberations == deliberations_registry


# =============================================================================
# Execute - Empty Registry Tests
# =============================================================================

class TestGetActiveJobsEmpty:
    """Test behavior with empty registry."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_deliberations(self):
        """Should return empty list when registry is empty."""
        deliberations_registry = {}

        use_case = GetActiveJobsUseCase(
            deliberations_registry=deliberations_registry,
        )

        jobs = await use_case.execute()

        assert jobs == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_all_completed(self):
        """Should return empty list when all deliberations completed."""
        deliberations_registry = {
            "delib-1": {"status": "completed", "start_time": time.time()},
            "delib-2": {"status": "failed", "start_time": time.time()},
        }

        use_case = GetActiveJobsUseCase(
            deliberations_registry=deliberations_registry,
        )

        jobs = await use_case.execute()

        assert jobs == []


# =============================================================================
# Execute - Running Jobs Tests
# =============================================================================

class TestGetActiveJobsRunning:
    """Test behavior with running deliberations."""

    @pytest.mark.asyncio
    async def test_returns_running_deliberations_only(self):
        """Should return only running deliberations."""
        start_time = time.time()
        deliberations_registry = {
            "delib-1": {
                "status": "running",
                "start_time": start_time,
                "role": "ARCHITECT",
                "task_id": "task-1",
            },
            "delib-2": {
                "status": "completed",
                "start_time": start_time,
                "role": "DEV",
                "task_id": "task-2",
            },
            "delib-3": {
                "status": "running",
                "start_time": start_time,
                "role": "QA",
                "task_id": "task-3",
            },
        }

        use_case = GetActiveJobsUseCase(
            deliberations_registry=deliberations_registry,
        )

        jobs = await use_case.execute()

        assert len(jobs) == 2
        job_ids = [job.job_id for job in jobs]
        assert "delib-1" in job_ids
        assert "delib-3" in job_ids
        assert "delib-2" not in job_ids  # Completed, not included

    @pytest.mark.asyncio
    async def test_creates_job_info_entities(self):
        """Should create JobInfo entities with correct fields."""
        start_time = time.time() - 125  # Started 125 seconds ago
        deliberations_registry = {
            "delib-123": {
                "status": "running",
                "start_time": start_time,
                "role": "ARCHITECT",
                "task_id": "task-456",
            }
        }

        use_case = GetActiveJobsUseCase(
            deliberations_registry=deliberations_registry,
        )

        jobs = await use_case.execute()

        assert len(jobs) == 1
        job = jobs[0]
        
        assert isinstance(job, JobInfo)
        assert job.job_id == "delib-123"
        assert job.name == "vllm-agent-job-delib-123"
        assert job.status == "RUNNING"
        assert job.submission_id == "delib-123"
        assert job.role == "ARCHITECT"
        assert job.task_id == "task-456"
        assert job.start_time_seconds == int(start_time)
        assert "m" in job.runtime
        assert "s" in job.runtime

    @pytest.mark.asyncio
    async def test_calculates_runtime_correctly(self):
        """Should calculate runtime in minutes and seconds."""
        start_time = time.time() - 185  # Started 185 seconds ago (3m 5s)
        deliberations_registry = {
            "delib-123": {
                "status": "running",
                "start_time": start_time,
                "role": "DEV",
                "task_id": "task-1",
            }
        }

        use_case = GetActiveJobsUseCase(
            deliberations_registry=deliberations_registry,
        )

        jobs = await use_case.execute()

        job = jobs[0]
        # Runtime should be approximately "3m 5s"
        assert "3m" in job.runtime
        assert "s" in job.runtime


# =============================================================================
# Execute - Edge Cases Tests
# =============================================================================

class TestGetActiveJobsEdgeCases:
    """Test edge cases."""

    @pytest.mark.asyncio
    async def test_handles_missing_optional_fields(self):
        """Should use defaults when optional fields missing."""
        deliberations_registry = {
            "delib-123": {
                "status": "running",
                # Missing: role, task_id, start_time
            }
        }

        use_case = GetActiveJobsUseCase(
            deliberations_registry=deliberations_registry,
        )

        jobs = await use_case.execute()

        assert len(jobs) == 1
        job = jobs[0]
        assert job.role == "UNKNOWN"  # Default
        assert job.task_id == "unknown"  # Default
        assert job.start_time_seconds > 0  # Uses current time

    @pytest.mark.asyncio
    async def test_handles_multiple_running_jobs(self):
        """Should handle multiple running deliberations."""
        start_time = time.time()
        deliberations_registry = {}
        
        # Create 5 running deliberations
        for i in range(5):
            deliberations_registry[f"delib-{i}"] = {
                "status": "running",
                "start_time": start_time,
                "role": f"ROLE-{i}",
                "task_id": f"task-{i}",
            }

        use_case = GetActiveJobsUseCase(
            deliberations_registry=deliberations_registry,
        )

        jobs = await use_case.execute()

        assert len(jobs) == 5
        assert all(job.status == "RUNNING" for job in jobs)

    @pytest.mark.asyncio
    async def test_runtime_zero_seconds(self):
        """Should handle deliberations that just started."""
        start_time = time.time()  # Just now
        deliberations_registry = {
            "delib-123": {
                "status": "running",
                "start_time": start_time,
                "role": "DEV",
                "task_id": "task-1",
            }
        }

        use_case = GetActiveJobsUseCase(
            deliberations_registry=deliberations_registry,
        )

        jobs = await use_case.execute()

        job = jobs[0]
        # Should be "0m 0s" or similar
        assert "0m" in job.runtime or "1m" in job.runtime

