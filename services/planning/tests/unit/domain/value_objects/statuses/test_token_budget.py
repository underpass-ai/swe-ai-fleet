"""Unit tests for TokenBudget enum."""

import pytest
from planning.domain.value_objects.statuses.token_budget import TokenBudget


class TestTokenBudget:
    """Test suite for TokenBudget enum."""

    def test_standard_value(self) -> None:
        """Test STANDARD token budget value."""
        assert TokenBudget.STANDARD == 2000
        assert TokenBudget.STANDARD.value == 2000

    def test_large_value(self) -> None:
        """Test LARGE token budget value."""
        assert TokenBudget.LARGE == 4000
        assert TokenBudget.LARGE.value == 4000

    def test_small_value(self) -> None:
        """Test SMALL token budget value."""
        assert TokenBudget.SMALL == 1000
        assert TokenBudget.SMALL.value == 1000

    def test_all_values(self) -> None:
        """Test all token budget values are defined."""
        budgets = [TokenBudget.SMALL, TokenBudget.STANDARD, TokenBudget.LARGE]
        values = [budget.value for budget in budgets]

        assert TokenBudget.SMALL.value == 1000
        assert TokenBudget.STANDARD.value == 2000
        assert TokenBudget.LARGE.value == 4000
        assert len(values) == 3
        assert all(isinstance(v, int) for v in values)
        assert all(v > 0 for v in values)

    def test_string_representation(self) -> None:
        """Test string representation of token budget."""
        assert str(TokenBudget.STANDARD) == "2000"
        assert str(TokenBudget.LARGE) == "4000"
        assert str(TokenBudget.SMALL) == "1000"

    def test_comparison(self) -> None:
        """Test comparison between token budgets."""
        assert TokenBudget.SMALL < TokenBudget.STANDARD
        assert TokenBudget.STANDARD < TokenBudget.LARGE
        assert TokenBudget.SMALL < TokenBudget.LARGE

    def test_int_enum_behavior(self) -> None:
        """Test that TokenBudget behaves as IntEnum."""
        # Can compare with integers
        assert TokenBudget.STANDARD == 2000
        assert TokenBudget.STANDARD != 3000

        # Can use in arithmetic (if needed)
        total = TokenBudget.SMALL.value + TokenBudget.STANDARD.value
        assert total == 3000

