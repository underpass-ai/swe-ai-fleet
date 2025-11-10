"""Unit tests for TokenBudgetCalculator domain service."""

import pytest
from core.context.domain.role import Role
from core.context.domain.services.token_budget_calculator import TokenBudgetCalculator


def test_calculate_for_architect_role():
    """Test that architect gets higher base token budget."""
    calculator = TokenBudgetCalculator()

    result = calculator.calculate(
        role=Role.ARCHITECT,
        task_count=0,
        decision_count=0,
    )

    # Architect base is 8192 (higher than default 4096)
    assert result == 8192


def test_calculate_for_developer_role():
    """Test that developer gets default base token budget."""
    calculator = TokenBudgetCalculator()

    result = calculator.calculate(
        role=Role.DEVELOPER,
        task_count=0,
        decision_count=0,
    )

    # Developer base is 4096 (default)
    assert result == 4096


def test_calculate_with_tasks_increases_budget():
    """Test that task count increases token budget."""
    calculator = TokenBudgetCalculator()

    result = calculator.calculate(
        role=Role.DEVELOPER,
        task_count=10,  # 10 tasks * 256 = 2560 bump
        decision_count=0,
    )

    # base 4096 + bump 2560 = 6656
    assert result == 6656


def test_calculate_with_decisions_increases_budget():
    """Test that decision count increases token budget."""
    calculator = TokenBudgetCalculator()

    result = calculator.calculate(
        role=Role.DEVELOPER,
        task_count=0,
        decision_count=10,  # 10 decisions * 128 = 1280 bump
    )

    # base 4096 + bump 1280 = 5376
    assert result == 5376


def test_calculate_with_tasks_and_decisions():
    """Test combined bump from tasks and decisions."""
    calculator = TokenBudgetCalculator()

    result = calculator.calculate(
        role=Role.DEVELOPER,
        task_count=5,   # 5 * 256 = 1280
        decision_count=8,  # 8 * 128 = 1024
    )

    # base 4096 + bump 2304 (1280+1024) = 6400
    assert result == 6400


def test_calculate_bump_capped_at_maximum():
    """Test that bump is capped at bump_max."""
    calculator = TokenBudgetCalculator()

    result = calculator.calculate(
        role=Role.DEVELOPER,
        task_count=100,  # Would be 25600, but capped at 4096
        decision_count=100,  # Would be 12800, but capped at 4096
    )

    # base 4096 + bump_max 4096 = 8192
    assert result == 8192


def test_calculate_raises_on_negative_task_count():
    """Test that negative task count raises ValueError (fail-fast)."""
    calculator = TokenBudgetCalculator()

    with pytest.raises(ValueError, match="task_count cannot be negative"):
        calculator.calculate(
            role=Role.DEVELOPER,
            task_count=-1,
            decision_count=0,
        )


def test_calculate_raises_on_negative_decision_count():
    """Test that negative decision count raises ValueError (fail-fast)."""
    calculator = TokenBudgetCalculator()

    with pytest.raises(ValueError, match="decision_count cannot be negative"):
        calculator.calculate(
            role=Role.DEVELOPER,
            task_count=0,
            decision_count=-1,
        )


def test_calculate_with_custom_configuration():
    """Test that custom configuration values are respected."""
    calculator = TokenBudgetCalculator(
        base_architect=10000,
        base_default=5000,
        bump_per_task=500,
        bump_per_decision=250,
        bump_max=8000,
    )

    result = calculator.calculate(
        role=Role.DEVELOPER,
        task_count=2,  # 2 * 500 = 1000
        decision_count=4,  # 4 * 250 = 1000
    )

    # base 5000 + bump 2000 = 7000
    assert result == 7000


def test_calculate_for_full_access_role_with_no_data():
    """Test full access role with no tasks/decisions."""
    calculator = TokenBudgetCalculator()

    result = calculator.calculate_for_full_access_role(
        total_tasks=0,
        total_decisions=0,
    )

    # Full access gets architect base: 8192
    assert result == 8192


def test_calculate_for_full_access_role_with_data():
    """Test full access role with tasks and decisions."""
    calculator = TokenBudgetCalculator()

    result = calculator.calculate_for_full_access_role(
        total_tasks=10,  # 10 * 256 = 2560
        total_decisions=5,  # 5 * 128 = 640
    )

    # base 8192 + bump 3200 = 11392
    assert result == 11392


def test_calculate_for_full_access_role_bump_capped():
    """Test that full access role bump is also capped."""
    calculator = TokenBudgetCalculator()

    result = calculator.calculate_for_full_access_role(
        total_tasks=100,  # Would be 25600, but capped
        total_decisions=100,  # Would be 12800, but capped
    )

    # base 8192 + bump_max 4096 = 12288
    assert result == 12288


def test_calculate_for_qa_role():
    """Test QA role uses default base (not architect)."""
    calculator = TokenBudgetCalculator()

    result = calculator.calculate(
        role=Role.QA,
        task_count=0,
        decision_count=0,
    )

    # QA uses default base: 4096
    assert result == 4096


def test_calculate_architect_with_large_context():
    """Test architect with large context gets appropriate budget."""
    calculator = TokenBudgetCalculator()

    result = calculator.calculate(
        role=Role.ARCHITECT,
        task_count=20,  # 20 * 256 = 5120 (capped at 4096)
        decision_count=0,
    )

    # base 8192 + bump_max 4096 = 12288
    assert result == 12288

