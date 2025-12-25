"""Unit tests for PoNotes value object."""

import pytest
from planning.domain.value_objects.review.po_notes import PoNotes


def test_po_notes_creation_success() -> None:
    """Test successful PoNotes creation."""
    # Arrange & Act
    notes = PoNotes("This plan aligns with business goals and has clear acceptance criteria.")

    # Assert
    assert notes.value == "This plan aligns with business goals and has clear acceptance criteria."


def test_po_notes_is_immutable() -> None:
    """Test that PoNotes is frozen (immutable)."""
    # Arrange
    notes = PoNotes("Approved")

    # Act & Assert
    with pytest.raises(Exception):  # FrozenInstanceError
        notes.value = "Changed"  # type: ignore


def test_po_notes_rejects_empty_string() -> None:
    """Test that PoNotes rejects empty string."""
    # Act & Assert
    with pytest.raises(ValueError, match="PoNotes cannot be empty"):
        PoNotes("")


def test_po_notes_rejects_whitespace_only() -> None:
    """Test that PoNotes rejects whitespace-only string."""
    # Act & Assert
    with pytest.raises(ValueError, match="PoNotes cannot be empty"):
        PoNotes("   \n\t  ")


def test_po_notes_accepts_multiline() -> None:
    """Test that PoNotes accepts multiline text."""
    # Arrange
    multiline_notes = "Line 1: Good structure\nLine 2: Clear acceptance criteria\nLine 3: Ready to proceed"

    # Act
    notes = PoNotes(multiline_notes)

    # Assert
    assert "Line 1" in notes.value
    assert "Line 2" in notes.value
    assert "Line 3" in notes.value


def test_po_notes_accepts_special_characters() -> None:
    """Test that PoNotes accepts special characters."""
    # Arrange
    special_chars = "Approved! Plan has 100% clarity & good structure. Cost: $5k-$10k."

    # Act
    notes = PoNotes(special_chars)

    # Assert
    assert "Approved!" in notes.value
    assert "100%" in notes.value
    assert "&" in notes.value
    assert "$5k-$10k" in notes.value


def test_po_notes_accepts_long_text() -> None:
    """Test that PoNotes accepts very long text."""
    # Arrange
    long_text = "A" * 10000  # 10k characters

    # Act
    notes = PoNotes(long_text)

    # Assert
    assert len(notes.value) == 10000


def test_po_notes_str_representation() -> None:
    """Test string representation."""
    # Arrange
    notes = PoNotes("Plan looks good")

    # Act & Assert
    assert str(notes) == "Plan looks good"


def test_po_notes_repr_representation_short() -> None:
    """Test repr representation for short text."""
    # Arrange
    notes = PoNotes("Short text")

    # Act
    repr_str = repr(notes)

    # Assert
    assert "PoNotes" in repr_str
    assert "Short text" in repr_str


def test_po_notes_repr_representation_long() -> None:
    """Test repr representation for long text (truncated)."""
    # Arrange
    long_text = "A" * 100
    notes = PoNotes(long_text)

    # Act
    repr_str = repr(notes)

    # Assert
    assert "PoNotes" in repr_str
    assert "..." in repr_str  # Should be truncated


def test_po_notes_equality() -> None:
    """Test that two PoNotes with same value are equal."""
    # Arrange
    notes1 = PoNotes("Approved")
    notes2 = PoNotes("Approved")

    # Act & Assert
    assert notes1 == notes2


def test_po_notes_inequality() -> None:
    """Test that PoNotes with different values are not equal."""
    # Arrange
    notes1 = PoNotes("Approved A")
    notes2 = PoNotes("Approved B")

    # Act & Assert
    assert notes1 != notes2


def test_po_notes_hash_consistency() -> None:
    """Test that PoNotes can be hashed (for use in sets/dicts)."""
    # Arrange
    notes1 = PoNotes("Approved")
    notes2 = PoNotes("Approved")

    # Act & Assert: Same values = same hash
    assert hash(notes1) == hash(notes2)

    # Can be used in set
    notes_set = {notes1, notes2}
    assert len(notes_set) == 1  # Only one unique notes


def test_po_notes_semantic_traceability_message() -> None:
    """Test that error messages emphasize semantic traceability."""
    # Act & Assert
    try:
        PoNotes("")
        pytest.fail("Should have raised ValueError")
    except ValueError as e:
        # Check that error message mentions semantic traceability
        assert "semantic traceability" in str(e).lower()
        assert "accountability" in str(e).lower()


def test_po_notes_strips_leading_trailing_whitespace_in_validation() -> None:
    """Test that PoNotes validation strips whitespace for checking."""
    # Arrange - text with meaningful content but whitespace
    notes = PoNotes("  Approved with whitespace  ")

    # Assert - value is preserved as-is (no mutation)
    assert notes.value == "  Approved with whitespace  "
    # But validation checks stripped version
    assert notes.value.strip() == "Approved with whitespace"


def test_po_notes_with_unicode_characters() -> None:
    """Test that PoNotes accepts unicode characters."""
    # Arrange
    unicode_text = "Aprobado ✅ Plan tiene 100% claridad & buena estructura. Costo: €5k-€10k."

    # Act
    notes = PoNotes(unicode_text)

    # Assert
    assert "✅" in notes.value
    assert "€" in notes.value

