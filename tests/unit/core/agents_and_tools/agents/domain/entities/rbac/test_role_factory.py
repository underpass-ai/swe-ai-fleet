"""Unit tests for RoleFactory."""

import pytest

from core.agents_and_tools.agents.domain.entities.rbac.action import (
    Action,
    ActionEnum,
    ScopeEnum,
)
from core.agents_and_tools.agents.domain.entities.rbac.role import Role, RoleEnum
from core.agents_and_tools.agents.domain.entities.rbac.role_factory import RoleFactory


class TestRoleFactoryArchitect:
    """Test RoleFactory.create_architect()."""

    def test_create_architect_returns_valid_role(self):
        """Test create_architect returns architect role with correct config."""
        role = RoleFactory.create_architect()

        assert role.value == RoleEnum.ARCHITECT
        assert role.scope == ScopeEnum.TECHNICAL
        assert role.get_name() == "architect"

    def test_architect_can_approve_design(self):
        """Test architect can approve design."""
        role = RoleFactory.create_architect()

        assert ActionEnum.APPROVE_DESIGN in role.allowed_actions

    def test_architect_can_reject_design(self):
        """Test architect can reject design."""
        role = RoleFactory.create_architect()

        assert ActionEnum.REJECT_DESIGN in role.allowed_actions

    def test_architect_can_review_architecture(self):
        """Test architect can review architecture."""
        role = RoleFactory.create_architect()

        assert ActionEnum.REVIEW_ARCHITECTURE in role.allowed_actions


class TestRoleFactoryQA:
    """Test RoleFactory.create_qa()."""

    def test_create_qa_returns_valid_role(self):
        """Test create_qa returns QA role with correct config."""
        role = RoleFactory.create_qa()

        assert role.value == RoleEnum.QA
        assert role.scope == ScopeEnum.QUALITY
        assert role.get_name() == "qa"

    def test_qa_can_validate_compliance(self):
        """Test QA can validate compliance."""
        role = RoleFactory.create_qa()

        assert ActionEnum.VALIDATE_COMPLIANCE in role.allowed_actions

    def test_qa_can_validate_spec(self):
        """Test QA can validate spec."""
        role = RoleFactory.create_qa()

        assert ActionEnum.VALIDATE_SPEC in role.allowed_actions

    def test_qa_cannot_approve_design(self):
        """Test QA cannot approve technical design (wrong scope)."""
        role = RoleFactory.create_qa()

        assert ActionEnum.APPROVE_DESIGN not in role.allowed_actions


class TestRoleFactoryDeveloper:
    """Test RoleFactory.create_developer()."""

    def test_create_developer_returns_valid_role(self):
        """Test create_developer returns developer role."""
        role = RoleFactory.create_developer()

        assert role.value == RoleEnum.DEVELOPER
        assert role.scope == ScopeEnum.TECHNICAL
        assert role.get_name() == "developer"

    def test_developer_can_execute_task(self):
        """Test developer can execute tasks."""
        role = RoleFactory.create_developer()

        assert ActionEnum.EXECUTE_TASK in role.allowed_actions

    def test_developer_can_commit_code(self):
        """Test developer can commit code."""
        role = RoleFactory.create_developer()

        assert ActionEnum.COMMIT_CODE in role.allowed_actions

    def test_developer_cannot_approve_design(self):
        """Test developer cannot approve design (only architect can)."""
        role = RoleFactory.create_developer()

        assert ActionEnum.APPROVE_DESIGN not in role.allowed_actions


class TestRoleFactoryPO:
    """Test RoleFactory.create_po()."""

    def test_create_po_returns_valid_role(self):
        """Test create_po returns PO role."""
        role = RoleFactory.create_po()

        assert role.value == RoleEnum.PO
        assert role.scope == ScopeEnum.BUSINESS
        assert role.get_name() == "po"

    def test_po_can_approve_proposal(self):
        """Test PO can approve business proposals."""
        role = RoleFactory.create_po()

        assert ActionEnum.APPROVE_PROPOSAL in role.allowed_actions

    def test_po_can_reject_proposal(self):
        """Test PO can reject proposals."""
        role = RoleFactory.create_po()

        assert ActionEnum.REJECT_PROPOSAL in role.allowed_actions

    def test_po_can_modify_constraints(self):
        """Test PO can modify constraints."""
        role = RoleFactory.create_po()

        assert ActionEnum.MODIFY_CONSTRAINTS in role.allowed_actions


class TestRoleFactoryDevOps:
    """Test RoleFactory.create_devops()."""

    def test_create_devops_returns_valid_role(self):
        """Test create_devops returns devops role."""
        role = RoleFactory.create_devops()

        assert role.value == RoleEnum.DEVOPS
        assert role.scope == ScopeEnum.OPERATIONS
        assert role.get_name() == "devops"

    def test_devops_can_deploy_service(self):
        """Test devops can deploy services."""
        role = RoleFactory.create_devops()

        assert ActionEnum.DEPLOY_SERVICE in role.allowed_actions

    def test_devops_can_configure_infra(self):
        """Test devops can configure infrastructure."""
        role = RoleFactory.create_devops()

        assert ActionEnum.CONFIGURE_INFRA in role.allowed_actions


class TestRoleFactoryData:
    """Test RoleFactory.create_data()."""

    def test_create_data_returns_valid_role(self):
        """Test create_data returns data role."""
        role = RoleFactory.create_data()

        assert role.value == RoleEnum.DATA
        assert role.scope == ScopeEnum.DATA
        assert role.get_name() == "data"

    def test_data_can_execute_migration(self):
        """Test data can execute migrations."""
        role = RoleFactory.create_data()

        assert ActionEnum.EXECUTE_MIGRATION in role.allowed_actions

    def test_data_can_validate_schema(self):
        """Test data can validate schema."""
        role = RoleFactory.create_data()

        assert ActionEnum.VALIDATE_SCHEMA in role.allowed_actions


class TestRoleFactoryByName:
    """Test RoleFactory.create_role_by_name()."""

    @pytest.mark.parametrize(
        "role_name,expected_enum",
        [
            ("architect", RoleEnum.ARCHITECT),
            ("ARCHITECT", RoleEnum.ARCHITECT),  # Case insensitive
            ("qa", RoleEnum.QA),
            ("QA", RoleEnum.QA),
            ("developer", RoleEnum.DEVELOPER),
            ("DEVELOPER", RoleEnum.DEVELOPER),
            ("po", RoleEnum.PO),
            ("PO", RoleEnum.PO),
            ("devops", RoleEnum.DEVOPS),
            ("DEVOPS", RoleEnum.DEVOPS),
            ("data", RoleEnum.DATA),
            ("DATA", RoleEnum.DATA),
        ],
    )
    def test_create_role_by_name_returns_correct_role(self, role_name, expected_enum):
        """Test create_role_by_name returns correct role (case insensitive)."""
        role = RoleFactory.create_role_by_name(role_name)

        assert role.value == expected_enum

    def test_create_role_by_invalid_name_fails(self):
        """Test fail-fast on invalid role name."""
        with pytest.raises(ValueError, match="Unknown role"):
            RoleFactory.create_role_by_name("invalid_role")


class TestRBACEnforcement:
    """Integration tests for RBAC enforcement."""

    def test_architect_can_approve_technical_design(self):
        """Test architect can approve technical design action."""
        architect = RoleFactory.create_architect()
        approve_design = Action(value=ActionEnum.APPROVE_DESIGN)

        assert architect.can_perform(approve_design) is True

    def test_qa_cannot_approve_technical_design(self):
        """Test QA cannot approve technical design (wrong scope)."""
        qa = RoleFactory.create_qa()
        approve_design = Action(value=ActionEnum.APPROVE_DESIGN)

        assert qa.can_perform(approve_design) is False

    def test_qa_can_validate_spec(self):
        """Test QA can validate spec (quality scope)."""
        qa = RoleFactory.create_qa()
        validate_spec = Action(value=ActionEnum.VALIDATE_SPEC)

        assert qa.can_perform(validate_spec) is True

    def test_po_can_approve_business_proposal(self):
        """Test PO can approve business proposal."""
        po = RoleFactory.create_po()
        approve_proposal = Action(value=ActionEnum.APPROVE_PROPOSAL)

        assert po.can_perform(approve_proposal) is True

    def test_po_cannot_approve_technical_design(self):
        """Test PO cannot approve technical design (wrong scope)."""
        po = RoleFactory.create_po()
        approve_design = Action(value=ActionEnum.APPROVE_DESIGN)

        assert po.can_perform(approve_design) is False

    def test_developer_can_execute_task(self):
        """Test developer can execute tasks."""
        developer = RoleFactory.create_developer()
        execute_task = Action(value=ActionEnum.EXECUTE_TASK)

        assert developer.can_perform(execute_task) is True

    def test_developer_cannot_approve_design(self):
        """Test developer cannot approve design (only architect can)."""
        developer = RoleFactory.create_developer()
        approve_design = Action(value=ActionEnum.APPROVE_DESIGN)

        assert developer.can_perform(approve_design) is False

    def test_devops_can_deploy(self):
        """Test devops can deploy services."""
        devops = RoleFactory.create_devops()
        deploy = Action(value=ActionEnum.DEPLOY_SERVICE)

        assert devops.can_perform(deploy) is True

    def test_data_can_execute_migration(self):
        """Test data can execute migrations."""
        data = RoleFactory.create_data()
        migration = Action(value=ActionEnum.EXECUTE_MIGRATION)

        assert data.can_perform(migration) is True

