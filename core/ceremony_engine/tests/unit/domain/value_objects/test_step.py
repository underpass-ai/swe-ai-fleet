"""Unit tests for Step value object."""

import pytest

from core.ceremony_engine.domain.value_objects.retry_policy import RetryPolicy
from core.ceremony_engine.domain.value_objects.step import Step
from core.ceremony_engine.domain.value_objects.step_handler_type import StepHandlerType


def test_step_happy_path() -> None:
    """Test creating a valid step."""
    step = Step(
        id="score_stories",
        state="SELECTING",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"operation": "calculate_dor_scores"},
    )

    assert step.id == "score_stories"
    assert step.state == "SELECTING"
    assert step.handler == StepHandlerType.AGGREGATION_STEP
    assert step.config == {"operation": "calculate_dor_scores"}
    assert step.retry is None
    assert step.timeout_seconds is None


def test_step_with_retry() -> None:
    """Test creating a step with retry policy."""
    retry = RetryPolicy(max_attempts=3, backoff_seconds=5)
    step = Step(
        id="process_data",
        state="PROCESSING",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"operation": "process"},
        retry=retry,
    )

    assert step.retry == retry
    assert step.retry.max_attempts == 3


def test_step_with_timeout() -> None:
    """Test creating a step with timeout."""
    step = Step(
        id="process_data",
        state="PROCESSING",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"operation": "process"},
        timeout_seconds=3600,
    )

    assert step.timeout_seconds == 3600


def test_step_rejects_empty_id() -> None:
    """Test that empty id raises ValueError."""
    with pytest.raises(ValueError, match="Step id cannot be empty"):
        Step(
            id="",
            state="STATE",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"key": "value"},
        )


def test_step_rejects_uppercase_id() -> None:
    """Test that uppercase id (not snake_case) raises ValueError."""
    with pytest.raises(ValueError, match="Step id must be snake_case"):
        Step(
            id="SCORE_STORIES",
            state="STATE",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"key": "value"},
        )


def test_step_rejects_mixed_case_id() -> None:
    """Test that mixed case id (not snake_case) raises ValueError."""
    with pytest.raises(ValueError, match="Step id must be snake_case"):
        Step(
            id="ScoreStories",
            state="STATE",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"key": "value"},
        )


def test_step_rejects_id_with_spaces() -> None:
    """Test that id with spaces raises ValueError."""
    with pytest.raises(ValueError, match="Step id must be snake_case"):
        Step(
            id="score stories",
            state="STATE",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"key": "value"},
        )


def test_step_allows_snake_case_id() -> None:
    """Test that valid snake_case id is accepted."""
    step = Step(
        id="score_stories_for_sprint",
        state="STATE",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"key": "value"},
    )
    assert step.id == "score_stories_for_sprint"


def test_step_rejects_empty_state() -> None:
    """Test that empty state raises ValueError."""
    with pytest.raises(ValueError, match="Step state cannot be empty"):
        Step(
            id="step_id",
            state="",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"key": "value"},
        )


def test_step_rejects_empty_config() -> None:
    """Test that empty config dict raises ValueError."""
    with pytest.raises(ValueError, match="Step config cannot be empty"):
        Step(
            id="step_id",
            state="STATE",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={},
        )


def test_step_rejects_non_dict_config() -> None:
    """Test that non-dict config raises ValueError."""
    with pytest.raises(ValueError, match="Step config must be a dict"):
        Step(
            id="step_id",
            state="STATE",
            handler=StepHandlerType.AGGREGATION_STEP,
            config="not_a_dict",  # type: ignore[arg-type]
        )


def test_step_rejects_zero_timeout() -> None:
    """Test that timeout_seconds = 0 raises ValueError."""
    with pytest.raises(ValueError, match="Step timeout_seconds must be > 0"):
        Step(
            id="step_id",
            state="STATE",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"key": "value"},
            timeout_seconds=0,
        )


def test_step_rejects_negative_timeout() -> None:
    """Test that negative timeout_seconds raises ValueError."""
    with pytest.raises(ValueError, match="Step timeout_seconds must be > 0"):
        Step(
            id="step_id",
            state="STATE",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"key": "value"},
            timeout_seconds=-1,
        )


def test_step_str_representation() -> None:
    """Test string representation of step."""
    step = Step(
        id="score_stories",
        state="STATE",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"key": "value"},
    )
    assert "score_stories" in str(step)
    assert "aggregation_step" in str(step)


def test_step_is_immutable() -> None:
    """Test that step is immutable (frozen dataclass)."""
    step = Step(
        id="step_id",
        state="STATE",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"key": "value"},
    )

    with pytest.raises(Exception):  # frozen dataclass raises exception on mutation
        step.id = "changed"  # type: ignore[misc]
