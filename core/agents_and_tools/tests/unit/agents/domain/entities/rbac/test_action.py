"""Unit tests for Action value object."""

import pytest
from core.shared.domain import (
    Action,
    ActionEnum,
    ScopeEnum,
)


class TestActionCreation:
    """Test Action value object creation."""

    def test_create_action_with_valid_enum(self):
        """Test creating action with valid ActionEnum."""
        action = Action(value=ActionEnum.APPROVE_DESIGN)

        assert action.value == ActionEnum.APPROVE_DESIGN
        assert isinstance(action.value, ActionEnum)


    def test_action_is_immutable(self):
        """Test action is frozen (immutable)."""
        action = Action(value=ActionEnum.EXECUTE_TASK)

        with pytest.raises(AttributeError):
            action.value = ActionEnum.APPROVE_DESIGN  # type: ignore


class TestActionScope:
    """Test Action scope methods."""

    def test_get_scope_technical(self):
        """Test get_scope returns correct scope for technical action."""
        action = Action(value=ActionEnum.APPROVE_DESIGN)

        assert action.get_scope() == ScopeEnum.TECHNICAL

    def test_get_scope_business(self):
        """Test get_scope returns correct scope for business action."""
        action = Action(value=ActionEnum.APPROVE_PROPOSAL)

        assert action.get_scope() == ScopeEnum.BUSINESS

    def test_get_scope_quality(self):
        """Test get_scope returns correct scope for quality action."""
        action = Action(value=ActionEnum.VALIDATE_COMPLIANCE)

        assert action.get_scope() == ScopeEnum.QUALITY

    def test_get_scope_operations(self):
        """Test get_scope returns correct scope for operations action."""
        action = Action(value=ActionEnum.DEPLOY_SERVICE)

        assert action.get_scope() == ScopeEnum.OPERATIONS

    def test_get_scope_data(self):
        """Test get_scope returns correct scope for data action."""
        action = Action(value=ActionEnum.EXECUTE_MIGRATION)

        assert action.get_scope() == ScopeEnum.DATA


class TestActionScopeChecks:
    """Test Action scope checking methods."""

    def test_is_technical_returns_true_for_technical_action(self):
        """Test is_technical returns True for technical actions."""
        action = Action(value=ActionEnum.APPROVE_DESIGN)

        assert action.is_technical() is True
        assert action.is_business() is False
        assert action.is_quality() is False

    def test_is_business_returns_true_for_business_action(self):
        """Test is_business returns True for business actions."""
        action = Action(value=ActionEnum.APPROVE_PROPOSAL)

        assert action.is_business() is True
        assert action.is_technical() is False
        assert action.is_quality() is False

    def test_is_quality_returns_true_for_quality_action(self):
        """Test is_quality returns True for quality actions."""
        action = Action(value=ActionEnum.VALIDATE_SPEC)

        assert action.is_quality() is True
        assert action.is_technical() is False
        assert action.is_business() is False

    def test_is_operations_returns_true_for_operations_action(self):
        """Test is_operations returns True for operations actions."""
        action = Action(value=ActionEnum.DEPLOY_SERVICE)

        assert action.is_operations() is True
        assert action.is_technical() is False

    def test_is_data_returns_true_for_data_action(self):
        """Test is_data returns True for data actions."""
        action = Action(value=ActionEnum.EXECUTE_MIGRATION)

        assert action.is_data() is True
        assert action.is_technical() is False


class TestActionStringRepresentation:
    """Test Action string conversion methods."""

    def test_to_string_returns_action_name(self):
        """Test to_string returns action name."""
        action = Action(value=ActionEnum.APPROVE_DESIGN)

        assert action.to_string() == "approve_design"

    def test_str_returns_action_name(self):
        """Test __str__ returns action name."""
        action = Action(value=ActionEnum.COMMIT_CODE)

        assert str(action) == "commit_code"


class TestActionEnumCoverage:
    """Test all ActionEnum values are valid."""

    @pytest.mark.parametrize(
        "action_enum",
        [
            ActionEnum.APPROVE_DESIGN,
            ActionEnum.REJECT_DESIGN,
            ActionEnum.REVIEW_ARCHITECTURE,
            ActionEnum.EXECUTE_TASK,
            ActionEnum.RUN_TESTS,
            ActionEnum.COMMIT_CODE,
            ActionEnum.APPROVE_PROPOSAL,
            ActionEnum.REJECT_PROPOSAL,
            ActionEnum.REQUEST_REFINEMENT,
            ActionEnum.APPROVE_SCOPE,
            ActionEnum.MODIFY_CONSTRAINTS,
            ActionEnum.APPROVE_TESTS,
            ActionEnum.REJECT_TESTS,
            ActionEnum.VALIDATE_COMPLIANCE,
            ActionEnum.VALIDATE_SPEC,
            ActionEnum.DEPLOY_SERVICE,
            ActionEnum.CONFIGURE_INFRA,
            ActionEnum.ROLLBACK_DEPLOYMENT,
            ActionEnum.EXECUTE_MIGRATION,
            ActionEnum.VALIDATE_SCHEMA,
        ],
    )
    def test_all_action_enums_can_create_action(self, action_enum):
        """Test all ActionEnum values can create valid Action."""
        action = Action(value=action_enum)

        assert action.value == action_enum
        assert isinstance(action.get_scope(), ScopeEnum)

