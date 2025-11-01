"""Unit tests for domain entities."""

import pytest
from services.ray_executor.domain.entities import (
    DeliberationResult,
    ExecutionStats,
    JobInfo,
)
from services.ray_executor.domain.value_objects import AgentConfig, TaskConstraints


def test_agent_config_validates_empty_agent_id():
    """Test that AgentConfig validates empty agent_id."""
    with pytest.raises(ValueError, match="agent_id cannot be empty"):
        AgentConfig(
            agent_id="",
            role="DEV",
            model="Qwen/Qwen2.5-Coder-7B-Instruct",
        )


def test_agent_config_validates_empty_role():
    """Test that AgentConfig validates empty role."""
    with pytest.raises(ValueError, match="role cannot be empty"):
        AgentConfig(
            agent_id="agent-1",
            role="",
            model="Qwen/Qwen2.5-Coder-7B-Instruct",
        )


def test_agent_config_validates_empty_model():
    """Test that AgentConfig validates empty model."""
    with pytest.raises(ValueError, match="model cannot be empty"):
        AgentConfig(
            agent_id="agent-1",
            role="DEV",
            model="",
        )


def test_task_constraints_validates_empty_story_id():
    """Test that TaskConstraints validates empty story_id."""
    with pytest.raises(ValueError, match="story_id cannot be empty"):
        TaskConstraints(
            story_id="",
            plan_id="plan-1",
        )


def test_task_constraints_validates_negative_timeout():
    """Test that TaskConstraints validates negative timeout."""
    with pytest.raises(ValueError, match="timeout_seconds must be positive"):
        TaskConstraints(
            story_id="story-1",
            plan_id="plan-1",
            timeout_seconds=-1,
        )


def test_task_constraints_validates_negative_retries():
    """Test that TaskConstraints validates negative max_retries."""
    with pytest.raises(ValueError, match="max_retries cannot be negative"):
        TaskConstraints(
            story_id="story-1",
            plan_id="plan-1",
            max_retries=-1,
        )


def test_task_constraints_happy_path():
    """Test TaskConstraints creation with valid values."""
    constraints = TaskConstraints(
        story_id="story-1",
        plan_id="plan-1",
        timeout_seconds=600,
        max_retries=5,
    )

    assert constraints.story_id == "story-1"
    assert constraints.plan_id == "plan-1"
    assert constraints.timeout_seconds == 600
    assert constraints.max_retries == 5


def test_deliberation_result_validates_empty_agent_id():
    """Test that DeliberationResult validates empty agent_id."""
    with pytest.raises(ValueError, match="agent_id cannot be empty"):
        DeliberationResult(
            agent_id="",
            proposal="Use JWT tokens",
            reasoning="JWT is stateless and scalable",
            score=0.95,
            metadata={},
        )


def test_deliberation_result_validates_score_range():
    """Test that DeliberationResult validates score range."""
    with pytest.raises(ValueError, match="score must be between 0.0 and 1.0"):
        DeliberationResult(
            agent_id="agent-1",
            proposal="Use JWT tokens",
            reasoning="JWT is stateless and scalable",
            score=1.5,  # Invalid score
            metadata={},
        )


def test_deliberation_result_happy_path():
    """Test DeliberationResult creation with valid values."""
    result = DeliberationResult(
        agent_id="agent-1",
        proposal="Use JWT tokens",
        reasoning="JWT is stateless and scalable",
        score=0.95,
        metadata={"execution_time": "2.5s", "tokens_used": "1234"},
    )

    assert result.agent_id == "agent-1"
    assert result.proposal == "Use JWT tokens"
    assert result.score == 0.95
    assert result.metadata["tokens_used"] == "1234"


def test_execution_stats_validates_negative_values():
    """Test that ExecutionStats validates all negative values."""
    # Test total_deliberations
    with pytest.raises(ValueError, match="total_deliberations cannot be negative"):
        ExecutionStats(
            total_deliberations=-1,
            active_deliberations=0,
            completed_deliberations=0,
            failed_deliberations=0,
            average_execution_time_ms=0.0,
        )

    # Test active_deliberations
    with pytest.raises(ValueError, match="active_deliberations cannot be negative"):
        ExecutionStats(
            total_deliberations=0,
            active_deliberations=-1,
            completed_deliberations=0,
            failed_deliberations=0,
            average_execution_time_ms=0.0,
        )


def test_job_info_validates_empty_job_id():
    """Test that JobInfo validates empty job_id."""
    with pytest.raises(ValueError, match="job_id cannot be empty"):
        JobInfo(
            job_id="",
            name="vllm-agent-job",
            status="RUNNING",
            submission_id="delib-123",
            role="DEV",
            task_id="task-123",
            start_time_seconds=1234567890,
            runtime="5m 30s",
        )


def test_job_info_validates_negative_start_time():
    """Test that JobInfo validates negative start_time."""
    with pytest.raises(ValueError, match="start_time_seconds cannot be negative"):
        JobInfo(
            job_id="job-123",
            name="vllm-agent-job",
            status="RUNNING",
            submission_id="delib-123",
            role="DEV",
            task_id="task-123",
            start_time_seconds=-1,
            runtime="5m 30s",
        )


def test_job_info_happy_path():
    """Test JobInfo creation with valid values."""
    job = JobInfo(
        job_id="job-123",
        name="vllm-agent-job-delib-123",
        status="RUNNING",
        submission_id="delib-123",
        role="DEV",
        task_id="task-123",
        start_time_seconds=1234567890,
        runtime="5m 30s",
    )

    assert job.job_id == "job-123"
    assert job.status == "RUNNING"
    assert job.role == "DEV"
    assert job.runtime == "5m 30s"

