"""Unit tests for DORScore value object."""

import pytest
from planning.domain.value_objects import DORScore


def test_dor_score_creation_success():
    """Test successful DORScore creation."""
    score = DORScore(85)
    assert score.value == 85


def test_dor_score_is_frozen():
    """Test that DORScore is immutable."""
    score = DORScore(50)

    with pytest.raises(Exception):  # FrozenInstanceError
        score.value = 100  # type: ignore


def test_dor_score_rejects_negative():
    """Test that DORScore rejects negative values."""
    with pytest.raises(ValueError, match="must be between 0 and 100"):
        DORScore(-1)


def test_dor_score_rejects_above_100():
    """Test that DORScore rejects values > 100."""
    with pytest.raises(ValueError, match="must be between 0 and 100"):
        DORScore(101)


def test_dor_score_rejects_non_integer():
    """Test that DORScore rejects non-integer values."""
    with pytest.raises(TypeError, match="must be an integer"):
        DORScore(85.5)  # type: ignore


def test_dor_score_boundary_values():
    """Test boundary values (0 and 100)."""
    min_score = DORScore(0)
    max_score = DORScore(100)

    assert min_score.value == 0
    assert max_score.value == 100


def test_dor_score_is_ready():
    """Test is_ready() business rule (score >= 80)."""
    assert DORScore(80).is_ready() is True
    assert DORScore(85).is_ready() is True
    assert DORScore(100).is_ready() is True
    assert DORScore(79).is_ready() is False
    assert DORScore(0).is_ready() is False


def test_dor_score_is_partially_ready():
    """Test is_partially_ready() business rule (50 <= score < 80)."""
    assert DORScore(50).is_partially_ready() is True
    assert DORScore(60).is_partially_ready() is True
    assert DORScore(79).is_partially_ready() is True
    assert DORScore(80).is_partially_ready() is False
    assert DORScore(49).is_partially_ready() is False


def test_dor_score_is_not_ready():
    """Test is_not_ready() business rule (score < 50)."""
    assert DORScore(0).is_not_ready() is True
    assert DORScore(25).is_not_ready() is True
    assert DORScore(49).is_not_ready() is True
    assert DORScore(50).is_not_ready() is False
    assert DORScore(80).is_not_ready() is False


def test_dor_score_str_representation():
    """Test string representation."""
    score = DORScore(75)
    assert str(score) == "75/100"

