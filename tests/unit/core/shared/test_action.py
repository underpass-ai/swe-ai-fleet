"""Unit tests for Action value object (Shared Kernel).

Tests Action domain logic and Tell, Don't Ask methods.
"""

import pytest
from core.shared.domain import Action, ActionEnum, ScopeEnum


def test_action_creation():
    """Test Action value object creation."""
    action = Action(value=ActionEnum.APPROVE_DESIGN)

    assert action.value == ActionEnum.APPROVE_DESIGN


def test_action_get_value():
    """Test Action.get_value() returns string."""
    action = Action(value=ActionEnum.COMMIT_CODE)

    assert action.get_value() == "commit_code"
    assert isinstance(action.get_value(), str)


def test_action_get_scope_technical():
    """Test get_scope() for technical actions."""
    action = Action(value=ActionEnum.APPROVE_DESIGN)

    assert action.get_scope() == ScopeEnum.TECHNICAL


def test_action_get_scope_business():
    """Test get_scope() for business actions."""
    action = Action(value=ActionEnum.APPROVE_STORY)

    assert action.get_scope() == ScopeEnum.BUSINESS


def test_action_get_scope_quality():
    """Test get_scope() for quality actions."""
    action = Action(value=ActionEnum.APPROVE_TESTS)

    assert action.get_scope() == ScopeEnum.QUALITY


def test_action_get_scope_workflow():
    """Test get_scope() for workflow actions."""
    action = Action(value=ActionEnum.CLAIM_TASK)

    assert action.get_scope() == ScopeEnum.WORKFLOW


def test_action_is_technical():
    """Test is_technical() method."""
    technical = Action(value=ActionEnum.COMMIT_CODE)
    business = Action(value=ActionEnum.APPROVE_STORY)

    assert technical.is_technical() is True
    assert business.is_technical() is False


def test_action_is_business():
    """Test is_business() method."""
    business = Action(value=ActionEnum.APPROVE_STORY)
    technical = Action(value=ActionEnum.COMMIT_CODE)

    assert business.is_business() is True
    assert technical.is_business() is False


def test_action_is_quality():
    """Test is_quality() method."""
    quality = Action(value=ActionEnum.APPROVE_TESTS)
    technical = Action(value=ActionEnum.COMMIT_CODE)

    assert quality.is_quality() is True
    assert technical.is_quality() is False


def test_action_is_workflow():
    """Test is_workflow() method."""
    workflow = Action(value=ActionEnum.CLAIM_TASK)
    business = Action(value=ActionEnum.APPROVE_STORY)

    assert workflow.is_workflow() is True
    assert business.is_workflow() is False


def test_action_is_rejection():
    """Test is_rejection() identifies rejection actions."""
    reject_design = Action(value=ActionEnum.REJECT_DESIGN)
    reject_tests = Action(value=ActionEnum.REJECT_TESTS)
    reject_story = Action(value=ActionEnum.REJECT_STORY)
    approve_design = Action(value=ActionEnum.APPROVE_DESIGN)

    assert reject_design.is_rejection() is True
    assert reject_tests.is_rejection() is True
    assert reject_story.is_rejection() is True
    assert approve_design.is_rejection() is False


def test_action_is_approval():
    """Test is_approval() identifies approval actions."""
    approve_design = Action(value=ActionEnum.APPROVE_DESIGN)
    approve_tests = Action(value=ActionEnum.APPROVE_TESTS)
    approve_story = Action(value=ActionEnum.APPROVE_STORY)
    reject_design = Action(value=ActionEnum.REJECT_DESIGN)

    assert approve_design.is_approval() is True
    assert approve_tests.is_approval() is True
    assert approve_story.is_approval() is True
    assert reject_design.is_approval() is False


def test_action_to_string():
    """Test to_string() method."""
    action = Action(value=ActionEnum.APPROVE_DESIGN)

    assert action.to_string() == "approve_design"


def test_action_str():
    """Test __str__() method for logging."""
    action = Action(value=ActionEnum.COMMIT_CODE)

    assert str(action) == "commit_code"


def test_action_immutable():
    """Test that Action is immutable (frozen=True)."""
    action = Action(value=ActionEnum.CLAIM_TASK)

    with pytest.raises(AttributeError):
        action.value = ActionEnum.COMMIT_CODE  # type: ignore


def test_action_no_action():
    """Test NO_ACTION semantic null."""
    action = Action(value=ActionEnum.NO_ACTION)

    assert action.get_value() == "no_action"
    assert action.is_workflow() is True


def test_all_actions_have_scope():
    """Test that all ActionEnum values have a scope defined."""
    from core.shared.domain.action_scopes import ACTION_SCOPES

    for action_enum in ActionEnum:
        assert action_enum in ACTION_SCOPES, f"{action_enum} missing in ACTION_SCOPES"


def test_action_enum_str_values():
    """Test that ActionEnum values are strings."""
    assert ActionEnum.APPROVE_DESIGN.value == "approve_design"
    assert ActionEnum.COMMIT_CODE.value == "commit_code"
    assert ActionEnum.CLAIM_TASK.value == "claim_task"


def test_action_equality():
    """Test Action equality (dataclass equality)."""
    action1 = Action(value=ActionEnum.APPROVE_DESIGN)
    action2 = Action(value=ActionEnum.APPROVE_DESIGN)
    action3 = Action(value=ActionEnum.REJECT_DESIGN)

    assert action1 == action2
    assert action1 != action3

