"""Unit tests for BacklogReviewCeremonyId value object."""

import pytest
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)


class TestBacklogReviewCeremonyId:
    """Test suite for BacklogReviewCeremonyId value object."""

    def test_create_valid_id(self) -> None:
        """Test creating a valid BacklogReviewCeremonyId."""
        ceremony_id = BacklogReviewCeremonyId(value="BRC-12345")

        assert ceremony_id.value == "BRC-12345"

    def test_create_with_uuid_format(self) -> None:
        """Test creating ID with UUID format."""
        ceremony_id = BacklogReviewCeremonyId(
            value="BRC-550e8400-e29b-41d4-a716-446655440000"
        )

        assert ceremony_id.value.startswith("BRC-")
        assert len(ceremony_id.value) > 10

    def test_empty_id_raises_value_error(self) -> None:
        """Test that empty ID raises ValueError."""
        with pytest.raises(ValueError, match="BacklogReviewCeremonyId cannot be empty"):
            BacklogReviewCeremonyId(value="")

    def test_whitespace_only_id_raises_value_error(self) -> None:
        """Test that whitespace-only ID raises ValueError."""
        with pytest.raises(ValueError, match="BacklogReviewCeremonyId cannot be empty"):
            BacklogReviewCeremonyId(value="   ")

    def test_whitespace_with_tabs_raises_value_error(self) -> None:
        """Test that tabs-only ID raises ValueError."""
        with pytest.raises(ValueError, match="BacklogReviewCeremonyId cannot be empty"):
            BacklogReviewCeremonyId(value="\t\n")

    def test_str_representation(self) -> None:
        """Test __str__ returns the value."""
        ceremony_id = BacklogReviewCeremonyId(value="BRC-12345")

        assert str(ceremony_id) == "BRC-12345"

    def test_equality(self) -> None:
        """Test equality between two IDs with same value."""
        id1 = BacklogReviewCeremonyId(value="BRC-12345")
        id2 = BacklogReviewCeremonyId(value="BRC-12345")

        assert id1 == id2

    def test_inequality(self) -> None:
        """Test inequality between two IDs with different values."""
        id1 = BacklogReviewCeremonyId(value="BRC-12345")
        id2 = BacklogReviewCeremonyId(value="BRC-67890")

        assert id1 != id2

    def test_immutability(self) -> None:
        """Test that BacklogReviewCeremonyId is immutable (frozen dataclass)."""
        ceremony_id = BacklogReviewCeremonyId(value="BRC-12345")

        with pytest.raises(AttributeError):
            ceremony_id.value = "BRC-99999"  # type: ignore

    def test_hash_consistency(self) -> None:
        """Test that IDs with same value have same hash."""
        id1 = BacklogReviewCeremonyId(value="BRC-12345")
        id2 = BacklogReviewCeremonyId(value="BRC-12345")

        assert hash(id1) == hash(id2)

    def test_can_be_used_in_set(self) -> None:
        """Test that IDs can be used in sets."""
        id1 = BacklogReviewCeremonyId(value="BRC-12345")
        id2 = BacklogReviewCeremonyId(value="BRC-67890")
        id3 = BacklogReviewCeremonyId(value="BRC-12345")

        id_set = {id1, id2, id3}

        assert len(id_set) == 2  # id1 and id3 are same

    def test_can_be_used_as_dict_key(self) -> None:
        """Test that IDs can be used as dictionary keys."""
        id1 = BacklogReviewCeremonyId(value="BRC-12345")
        id2 = BacklogReviewCeremonyId(value="BRC-67890")

        id_dict = {id1: "ceremony1", id2: "ceremony2"}

        assert id_dict[id1] == "ceremony1"
        assert id_dict[id2] == "ceremony2"

    def test_repr_contains_value(self) -> None:
        """Test __repr__ contains the value."""
        ceremony_id = BacklogReviewCeremonyId(value="BRC-12345")

        repr_str = repr(ceremony_id)
        assert "BRC-12345" in repr_str
        assert "BacklogReviewCeremonyId" in repr_str

