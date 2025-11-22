"""Unit tests for DecisionId value object."""

import pytest
from planning.domain.value_objects import DecisionId


def test_decision_id_creation_success():
    """Test successful DecisionId creation."""
    decision_id = DecisionId("decision-123")
    assert decision_id.value == "decision-123"


def test_decision_id_is_frozen():
    """Test that DecisionId is immutable."""
    decision_id = DecisionId("decision-456")

    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        decision_id.value = "new-id"  # type: ignore


def test_decision_id_rejects_empty_string():
    """Test that DecisionId rejects empty string."""
    with pytest.raises(ValueError, match="DecisionId cannot be empty"):
        DecisionId("")


def test_decision_id_rejects_whitespace():
    """Test that DecisionId rejects whitespace-only string."""
    with pytest.raises(ValueError, match="DecisionId cannot be empty"):
        DecisionId("   ")


def test_decision_id_str_representation():
    """Test string representation."""
    decision_id = DecisionId("decision-789")
    assert str(decision_id) == "decision-789"


def test_decision_id_equality():
    """Test that DecisionIds with same value are equal."""
    id1 = DecisionId("decision-abc")
    id2 = DecisionId("decision-abc")
    id3 = DecisionId("decision-xyz")

    assert id1 == id2
    assert id1 != id3


def test_decision_id_hash():
    """Test that DecisionIds can be used in sets/dicts."""
    id1 = DecisionId("decision-1")
    id2 = DecisionId("decision-2")
    id3 = DecisionId("decision-1")  # Same as id1

    decision_set = {id1, id2, id3}
    assert len(decision_set) == 2  # id1 and id3 are the same


def test_decision_id_with_special_characters():
    """Test DecisionId with valid special characters."""
    special_ids = [
        "decision-123-abc",
        "decision_456",
        "decision.789",
        "decision:abc:xyz",
    ]

    for id_value in special_ids:
        decision_id = DecisionId(id_value)
        assert decision_id.value == id_value

