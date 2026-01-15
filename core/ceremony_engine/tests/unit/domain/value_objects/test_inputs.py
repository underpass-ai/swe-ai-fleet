"""Unit tests for Inputs value object."""

import pytest

from core.ceremony_engine.domain.value_objects.inputs import Inputs


def test_inputs_happy_path() -> None:
    """Test creating valid inputs."""
    inputs = Inputs(required=("team_id", "sprint_goal"), optional=("deadline",))

    assert len(inputs.required) == 2
    assert "team_id" in inputs.required
    assert "sprint_goal" in inputs.required
    assert len(inputs.optional) == 1
    assert "deadline" in inputs.optional


def test_inputs_empty_optional() -> None:
    """Test creating inputs with empty optional."""
    inputs = Inputs(required=("team_id",), optional=())

    assert len(inputs.required) == 1
    assert len(inputs.optional) == 0


def test_inputs_rejects_empty_required_name() -> None:
    """Test that empty required input name raises ValueError."""
    with pytest.raises(ValueError, match="Required input name cannot be empty"):
        Inputs(required=("team_id", ""), optional=())


def test_inputs_rejects_whitespace_required_name() -> None:
    """Test that whitespace-only required input name raises ValueError."""
    with pytest.raises(ValueError, match="Required input name cannot be empty"):
        Inputs(required=("team_id", "   "), optional=())


def test_inputs_rejects_empty_optional_name() -> None:
    """Test that empty optional input name raises ValueError."""
    with pytest.raises(ValueError, match="Optional input name cannot be empty"):
        Inputs(required=("team_id",), optional=("deadline", ""))


def test_inputs_rejects_invalid_required_name() -> None:
    """Test that invalid required input name (not valid identifier) raises ValueError."""
    with pytest.raises(ValueError, match="Required input name must be valid identifier"):
        Inputs(required=("team-id",), optional=())  # hyphens not allowed


def test_inputs_rejects_invalid_optional_name() -> None:
    """Test that invalid optional input name (not valid identifier) raises ValueError."""
    with pytest.raises(ValueError, match="Optional input name must be valid identifier"):
        Inputs(required=("team_id",), optional=("dead line",))  # spaces not allowed


def test_inputs_allows_snake_case_names() -> None:
    """Test that valid snake_case names are accepted."""
    inputs = Inputs(
        required=("team_id", "sprint_goal", "candidate_story_ids"),
        optional=("capacity_constraints", "deadline"),
    )

    assert len(inputs.required) == 3
    assert len(inputs.optional) == 2


def test_inputs_rejects_duplicates() -> None:
    """Test that input names appearing in both required and optional raises ValueError."""
    with pytest.raises(ValueError, match="Input names cannot be both required and optional"):
        Inputs(required=("team_id", "sprint_goal"), optional=("team_id", "deadline"))


def test_inputs_allows_same_name_in_different_lists_if_different_case() -> None:
    """Test that same name with different case is considered different (edge case)."""
    # This is technically allowed by our validation (case-sensitive)
    inputs = Inputs(required=("team_id",), optional=("TEAM_ID",))
    assert "team_id" in inputs.required
    assert "TEAM_ID" in inputs.optional


def test_inputs_is_immutable() -> None:
    """Test that inputs is immutable (frozen dataclass)."""
    inputs = Inputs(required=("team_id",), optional=())

    with pytest.raises(Exception):  # frozen dataclass raises exception on mutation
        inputs.required = ("changed",)  # type: ignore[misc]


def test_inputs_required_is_tuple() -> None:
    """Test that required is stored as tuple (immutable)."""
    required_list = ["team_id", "sprint_goal"]
    inputs = Inputs(required=tuple(required_list), optional=())

    assert isinstance(inputs.required, tuple)
    # Tuple is immutable, so this should not affect the inputs
    required_list.append("deadline")
    assert len(inputs.required) == 2
