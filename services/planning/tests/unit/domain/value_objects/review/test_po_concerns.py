"""Unit tests for PoConcerns value object."""

import pytest
from planning.domain.value_objects.review.po_concerns import PoConcerns


def test_po_concerns_creation_success() -> None:
    """Test successful PoConcerns creation."""
    # Arrange & Act
    concerns = PoConcerns("Watch out for API rate limits in third-party integration.")

    # Assert
    assert concerns.value == "Watch out for API rate limits in third-party integration."


def test_po_concerns_is_immutable() -> None:
    """Test that PoConcerns is frozen (immutable)."""
    # Arrange
    concerns = PoConcerns("Monitor carefully")

    # Act & Assert
    with pytest.raises(Exception):  # FrozenInstanceError
        concerns.value = "Changed"  # type: ignore


def test_po_concerns_rejects_empty_string() -> None:
    """Test that PoConcerns rejects empty string."""
    # Act & Assert
    with pytest.raises(ValueError, match="PoConcerns cannot be empty"):
        PoConcerns("")


def test_po_concerns_rejects_whitespace_only() -> None:
    """Test that PoConcerns rejects whitespace-only string."""
    # Act & Assert
    with pytest.raises(ValueError, match="PoConcerns cannot be empty"):
        PoConcerns("   \n\t  ")


def test_po_concerns_accepts_multiline() -> None:
    """Test that PoConcerns accepts multiline text."""
    # Arrange
    multiline_concerns = "Concern 1: API limits\nConcern 2: Database performance\nConcern 3: Third-party reliability"

    # Act
    concerns = PoConcerns(multiline_concerns)

    # Assert
    assert "Concern 1" in concerns.value
    assert "Concern 2" in concerns.value
    assert "Concern 3" in concerns.value


def test_po_concerns_accepts_special_characters() -> None:
    """Test that PoConcerns accepts special characters."""
    # Arrange
    special_chars = "Watch API usage! Rate limits: 1000/min. Cost: $500-$1000/month."

    # Act
    concerns = PoConcerns(special_chars)

    # Assert
    assert "Watch API usage!" in concerns.value
    assert "1000/min" in concerns.value
    assert "$500-$1000" in concerns.value


def test_po_concerns_accepts_long_text() -> None:
    """Test that PoConcerns accepts very long text."""
    # Arrange
    long_text = "A" * 10000  # 10k characters

    # Act
    concerns = PoConcerns(long_text)

    # Assert
    assert len(concerns.value) == 10000


def test_po_concerns_str_representation() -> None:
    """Test string representation."""
    # Arrange
    concerns = PoConcerns("Monitor API usage")

    # Act & Assert
    assert str(concerns) == "Monitor API usage"


def test_po_concerns_repr_representation_short() -> None:
    """Test repr representation for short text."""
    # Arrange
    concerns = PoConcerns("Short concern")

    # Act
    repr_str = repr(concerns)

    # Assert
    assert "PoConcerns" in repr_str
    assert "Short concern" in repr_str


def test_po_concerns_repr_representation_long() -> None:
    """Test repr representation for long text (truncated)."""
    # Arrange
    long_text = "A" * 100
    concerns = PoConcerns(long_text)

    # Act
    repr_str = repr(concerns)

    # Assert
    assert "PoConcerns" in repr_str
    assert "..." in repr_str  # Should be truncated


def test_po_concerns_equality() -> None:
    """Test that two PoConcerns with same value are equal."""
    # Arrange
    concerns1 = PoConcerns("Monitor carefully")
    concerns2 = PoConcerns("Monitor carefully")

    # Act & Assert
    assert concerns1 == concerns2


def test_po_concerns_inequality() -> None:
    """Test that PoConcerns with different values are not equal."""
    # Arrange
    concerns1 = PoConcerns("Concern A")
    concerns2 = PoConcerns("Concern B")

    # Act & Assert
    assert concerns1 != concerns2


def test_po_concerns_hash_consistency() -> None:
    """Test that PoConcerns can be hashed (for use in sets/dicts)."""
    # Arrange
    concerns1 = PoConcerns("Monitor API")
    concerns2 = PoConcerns("Monitor API")

    # Act & Assert: Same values = same hash
    assert hash(concerns1) == hash(concerns2)

    # Can be used in set
    concerns_set = {concerns1, concerns2}
    assert len(concerns_set) == 1  # Only one unique concerns


def test_po_concerns_with_unicode_characters() -> None:
    """Test that PoConcerns accepts unicode characters."""
    # Arrange
    unicode_text = "Monitorear ⚠️ Límites de API: 1000/min. Costo: €500-€1000/mes."

    # Act
    concerns = PoConcerns(unicode_text)

    # Assert
    assert "⚠️" in concerns.value
    assert "€" in concerns.value

