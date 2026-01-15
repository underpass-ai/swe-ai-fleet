"""Unit tests for RetryPolicy value object."""

import pytest

from core.ceremony_engine.domain.value_objects.retry_policy import RetryPolicy


def test_retry_policy_happy_path() -> None:
    """Test creating a valid retry policy."""
    policy = RetryPolicy(max_attempts=3, backoff_seconds=5)

    assert policy.max_attempts == 3
    assert policy.backoff_seconds == 5
    assert policy.exponential_backoff is False


def test_retry_policy_with_exponential_backoff() -> None:
    """Test creating a retry policy with exponential backoff."""
    policy = RetryPolicy(max_attempts=3, backoff_seconds=5, exponential_backoff=True)

    assert policy.exponential_backoff is True


def test_retry_policy_rejects_max_attempts_zero() -> None:
    """Test that max_attempts < 1 raises ValueError."""
    with pytest.raises(ValueError, match="max_attempts must be >= 1"):
        RetryPolicy(max_attempts=0, backoff_seconds=5)


def test_retry_policy_rejects_max_attempts_negative() -> None:
    """Test that negative max_attempts raises ValueError."""
    with pytest.raises(ValueError, match="max_attempts must be >= 1"):
        RetryPolicy(max_attempts=-1, backoff_seconds=5)


def test_retry_policy_allows_backoff_zero() -> None:
    """Test that backoff_seconds can be 0 (no delay)."""
    policy = RetryPolicy(max_attempts=3, backoff_seconds=0)
    assert policy.backoff_seconds == 0


def test_retry_policy_rejects_negative_backoff() -> None:
    """Test that negative backoff_seconds raises ValueError."""
    with pytest.raises(ValueError, match="backoff_seconds must be >= 0"):
        RetryPolicy(max_attempts=3, backoff_seconds=-1)


def test_retry_policy_is_immutable() -> None:
    """Test that retry policy is immutable (frozen dataclass)."""
    policy = RetryPolicy(max_attempts=3, backoff_seconds=5)

    with pytest.raises(Exception):  # frozen dataclass raises exception on mutation
        policy.max_attempts = 5  # type: ignore[misc]
