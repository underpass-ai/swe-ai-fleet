"""Unit tests for domain entities."""

import pytest

from services.ray_executor.domain.entities import (
    DeliberationResult,
    ExecutionStats,
    JobInfo,
    MultiAgentDeliberationResult,
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
    assert result.score == pytest.approx(0.95)
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


# =============================================================================
# MultiAgentDeliberationResult Tests
# =============================================================================

def test_multi_agent_deliberation_result_validates_negative_total_agents():
    """Test that MultiAgentDeliberationResult validates negative total_agents."""
    with pytest.raises(ValueError, match="total_agents cannot be negative"):
        MultiAgentDeliberationResult(
            agent_results=[],
            total_agents=-1,
            completed_agents=0,
            failed_agents=0,
        )


def test_multi_agent_deliberation_result_validates_negative_completed_agents():
    """Test that MultiAgentDeliberationResult validates negative completed_agents."""
    with pytest.raises(ValueError, match="completed_agents cannot be negative"):
        MultiAgentDeliberationResult(
            agent_results=[],
            total_agents=3,
            completed_agents=-1,
            failed_agents=0,
        )


def test_multi_agent_deliberation_result_validates_negative_failed_agents():
    """Test that MultiAgentDeliberationResult validates negative failed_agents."""
    with pytest.raises(ValueError, match="failed_agents cannot be negative"):
        MultiAgentDeliberationResult(
            agent_results=[],
            total_agents=3,
            completed_agents=0,
            failed_agents=-1,
        )


def test_multi_agent_deliberation_result_validates_sum_exceeds_total():
    """Test that completed + failed cannot exceed total."""
    with pytest.raises(ValueError, match="cannot exceed total_agents"):
        MultiAgentDeliberationResult(
            agent_results=[],
            total_agents=3,
            completed_agents=2,
            failed_agents=2,
        )


def test_multi_agent_deliberation_result_validates_results_match_completed():
    """Test that agent_results count must match completed_agents."""
    result1 = DeliberationResult(
        agent_id="agent-1",
        proposal="Proposal 1",
        reasoning="Reasoning 1",
        score=0.9,
        metadata={},
    )

    with pytest.raises(ValueError, match="agent_results count.*must match"):
        MultiAgentDeliberationResult(
            agent_results=[result1],  # 1 result
            total_agents=3,
            completed_agents=2,  # But says 2 completed
            failed_agents=1,
        )


def test_multi_agent_deliberation_result_happy_path():
    """Test MultiAgentDeliberationResult creation with valid values."""
    result1 = DeliberationResult(
        agent_id="agent-1",
        proposal="Use microservices",
        reasoning="Better scalability",
        score=0.95,
        metadata={},
    )
    result2 = DeliberationResult(
        agent_id="agent-2",
        proposal="Use monolith",
        reasoning="Simpler to start",
        score=0.85,
        metadata={},
    )
    result3 = DeliberationResult(
        agent_id="agent-3",
        proposal="Use serverless",
        reasoning="Cost effective",
        score=0.90,
        metadata={},
    )

    multi_result = MultiAgentDeliberationResult(
        agent_results=[result1, result2, result3],
        total_agents=3,
        completed_agents=3,
        failed_agents=0,
    )

    assert len(multi_result.agent_results) == 3
    assert multi_result.total_agents == 3
    assert multi_result.completed_agents == 3
    assert multi_result.failed_agents == 0
    assert multi_result.all_completed is True
    assert multi_result.has_failures is False


def test_multi_agent_deliberation_result_best_result():
    """Test that best_result returns highest scoring result."""
    result1 = DeliberationResult(
        agent_id="agent-1",
        proposal="Proposal 1",
        reasoning="Reasoning 1",
        score=0.85,
        metadata={},
    )
    result2 = DeliberationResult(
        agent_id="agent-2",
        proposal="Proposal 2",
        reasoning="Reasoning 2",
        score=0.95,  # Highest score
        metadata={},
    )
    result3 = DeliberationResult(
        agent_id="agent-3",
        proposal="Proposal 3",
        reasoning="Reasoning 3",
        score=0.90,
        metadata={},
    )

    multi_result = MultiAgentDeliberationResult(
        agent_results=[result1, result2, result3],
        total_agents=3,
        completed_agents=3,
        failed_agents=0,
    )

    best = multi_result.best_result
    assert best is not None
    assert best.agent_id == "agent-2"
    assert best.score == pytest.approx(0.95)


def test_multi_agent_deliberation_result_best_result_none_when_empty():
    """Test that best_result returns None when no results."""
    multi_result = MultiAgentDeliberationResult(
        agent_results=[],
        total_agents=3,
        completed_agents=0,
        failed_agents=3,
    )

    assert multi_result.best_result is None


def test_multi_agent_deliberation_result_average_score():
    """Test that average_score calculates correctly."""
    result1 = DeliberationResult(
        agent_id="agent-1",
        proposal="Proposal 1",
        reasoning="Reasoning 1",
        score=0.8,
        metadata={},
    )
    result2 = DeliberationResult(
        agent_id="agent-2",
        proposal="Proposal 2",
        reasoning="Reasoning 2",
        score=0.9,
        metadata={},
    )
    result3 = DeliberationResult(
        agent_id="agent-3",
        proposal="Proposal 3",
        reasoning="Reasoning 3",
        score=1.0,
        metadata={},
    )

    multi_result = MultiAgentDeliberationResult(
        agent_results=[result1, result2, result3],
        total_agents=3,
        completed_agents=3,
        failed_agents=0,
    )

    # Average: (0.8 + 0.9 + 1.0) / 3 = 0.9
    assert multi_result.average_score == pytest.approx(0.9)


def test_multi_agent_deliberation_result_average_score_zero_when_empty():
    """Test that average_score returns 0.0 when no results."""
    multi_result = MultiAgentDeliberationResult(
        agent_results=[],
        total_agents=3,
        completed_agents=0,
        failed_agents=3,
    )

    assert multi_result.average_score == pytest.approx(0.0)


def test_multi_agent_deliberation_result_with_failures():
    """Test MultiAgentDeliberationResult with some failures."""
    result1 = DeliberationResult(
        agent_id="agent-1",
        proposal="Proposal 1",
        reasoning="Reasoning 1",
        score=0.9,
        metadata={},
    )
    result2 = DeliberationResult(
        agent_id="agent-2",
        proposal="Proposal 2",
        reasoning="Reasoning 2",
        score=0.85,
        metadata={},
    )

    multi_result = MultiAgentDeliberationResult(
        agent_results=[result1, result2],
        total_agents=3,
        completed_agents=2,
        failed_agents=1,
    )

    assert multi_result.all_completed is False
    assert multi_result.has_failures is True
    assert multi_result.completed_agents == 2
    assert multi_result.failed_agents == 1

