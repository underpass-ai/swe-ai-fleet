"""Unit tests for Keyword value object."""

from __future__ import annotations

import pytest

from core.shared.domain.value_objects.task_derivation.keyword import Keyword


class TestKeyword:
    """Tests for Keyword value object."""

    def test_keyword_rejects_blank_value(self) -> None:
        """Test that empty keyword is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Keyword("")

    def test_keyword_rejects_whitespace_only(self) -> None:
        """Test that whitespace-only keyword is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Keyword("   ")

    def test_valid_keyword_creates_instance(self) -> None:
        """Test that valid keyword creates instance."""
        keyword = Keyword("Graph")
        assert keyword.value == "Graph"

    def test_str_representation(self) -> None:
        """Test string representation."""
        keyword = Keyword("Graph")
        assert str(keyword) == "Graph"

    def test_matches_in_is_case_insensitive(self) -> None:
        """Test that matches_in is case-insensitive."""
        keyword = Keyword("Graph")

        assert keyword.matches_in("graph database ready")
        assert keyword.matches_in("GRAPH database ready")
        assert keyword.matches_in("Graph database ready")
        assert keyword.matches_in("Some graph here")

    def test_matches_in_returns_false_for_empty_text(self) -> None:
        """Test that matches_in returns False for empty text."""
        keyword = Keyword("Graph")
        assert not keyword.matches_in("")
        assert not keyword.matches_in(None)

    def test_matches_in_returns_false_when_not_found(self) -> None:
        """Test that matches_in returns False when keyword not found."""
        keyword = Keyword("Graph")
        assert not keyword.matches_in("Database ready")
        assert not keyword.matches_in("No match here")

