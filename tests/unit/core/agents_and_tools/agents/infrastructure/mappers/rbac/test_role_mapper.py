"""Unit tests for RoleMapper."""

import pytest

from core.agents_and_tools.agents.domain.entities.rbac import ActionEnum, Role, RoleEnum, ScopeEnum
from core.agents_and_tools.agents.infrastructure.dtos.role_dto import RoleDTO
from core.agents_and_tools.agents.infrastructure.mappers.rbac.role_mapper import RoleMapper


class TestRoleMapperDTOToEntity:
    """Test RoleMapper.dto_to_entity()."""

    def test_dto_to_entity_with_valid_dto(self):
        """Test converting valid DTO to entity."""
        dto = RoleDTO(
            name="architect",
            scope="technical",
            allowed_actions=["approve_design", "reject_design"],
        )

        role = RoleMapper.dto_to_entity(dto)

        assert role.value == RoleEnum.ARCHITECT
        assert role.scope == ScopeEnum.TECHNICAL
        assert ActionEnum.APPROVE_DESIGN in role.allowed_actions
        assert ActionEnum.REJECT_DESIGN in role.allowed_actions

    def test_dto_to_entity_normalizes_case(self):
        """Test DTO to entity handles uppercase input."""
        dto = RoleDTO(
            name="ARCHITECT",
            scope="TECHNICAL",
            allowed_actions=["APPROVE_DESIGN"],
        )

        role = RoleMapper.dto_to_entity(dto)

        assert role.value == RoleEnum.ARCHITECT
        assert role.scope == ScopeEnum.TECHNICAL

    def test_dto_to_entity_with_invalid_role_name_fails(self):
        """Test fail-fast on invalid role name."""
        dto = RoleDTO(
            name="invalid_role",
            scope="technical",
            allowed_actions=["approve_design"],
        )

        with pytest.raises(ValueError, match="Invalid role name"):
            RoleMapper.dto_to_entity(dto)

    def test_dto_to_entity_with_invalid_scope_fails(self):
        """Test fail-fast on invalid scope."""
        dto = RoleDTO(
            name="architect",
            scope="invalid_scope",
            allowed_actions=["approve_design"],
        )

        with pytest.raises(ValueError, match="Invalid scope"):
            RoleMapper.dto_to_entity(dto)

    def test_dto_to_entity_with_invalid_action_fails(self):
        """Test fail-fast on invalid action name."""
        dto = RoleDTO(
            name="architect",
            scope="technical",
            allowed_actions=["invalid_action"],
        )

        with pytest.raises(ValueError, match="Invalid action name"):
            RoleMapper.dto_to_entity(dto)


class TestRoleMapperEntityToDTO:
    """Test RoleMapper.entity_to_dto()."""

    def test_entity_to_dto_with_valid_entity(self):
        """Test converting valid entity to DTO."""
        role = Role(
            value=RoleEnum.ARCHITECT,
            allowed_actions=frozenset([ActionEnum.APPROVE_DESIGN, ActionEnum.REJECT_DESIGN]),
            scope=ScopeEnum.TECHNICAL,
        )

        dto = RoleMapper.entity_to_dto(role)

        assert dto.name == "architect"
        assert dto.scope == "technical"
        assert "approve_design" in dto.allowed_actions
        assert "reject_design" in dto.allowed_actions
        assert len(dto.allowed_actions) == 2

    def test_entity_to_dto_preserves_all_actions(self):
        """Test all allowed actions are converted to DTO."""
        role = Role(
            value=RoleEnum.QA,
            allowed_actions=frozenset([
                ActionEnum.VALIDATE_COMPLIANCE,
                ActionEnum.VALIDATE_SPEC,
                ActionEnum.APPROVE_TESTS,
                ActionEnum.REJECT_TESTS,
            ]),
            scope=ScopeEnum.QUALITY,
        )

        dto = RoleMapper.entity_to_dto(role)

        assert len(dto.allowed_actions) == 4
        assert "validate_compliance" in dto.allowed_actions
        assert "validate_spec" in dto.allowed_actions
        assert "approve_tests" in dto.allowed_actions
        assert "reject_tests" in dto.allowed_actions


class TestRoleMapperRoundTrip:
    """Test round-trip conversions (entity → DTO → entity)."""

    def test_entity_to_dto_to_entity_preserves_data(self):
        """Test round-trip conversion preserves all data."""
        original = Role(
            value=RoleEnum.DEVELOPER,
            allowed_actions=frozenset([
                ActionEnum.EXECUTE_TASK,
                ActionEnum.RUN_TESTS,
                ActionEnum.COMMIT_CODE,
            ]),
            scope=ScopeEnum.TECHNICAL,
        )

        dto = RoleMapper.entity_to_dto(original)
        reconstructed = RoleMapper.dto_to_entity(dto)

        assert reconstructed.value == original.value
        assert reconstructed.scope == original.scope
        assert reconstructed.allowed_actions == original.allowed_actions

    def test_dto_to_entity_to_dto_preserves_data(self):
        """Test reverse round-trip conversion preserves all data."""
        original_dto = RoleDTO(
            name="po",
            scope="business",
            allowed_actions=["approve_proposal", "reject_proposal"],
        )

        entity = RoleMapper.dto_to_entity(original_dto)
        reconstructed_dto = RoleMapper.entity_to_dto(entity)

        assert reconstructed_dto.name == original_dto.name
        assert reconstructed_dto.scope == original_dto.scope
        # Order might differ, so compare as sets
        assert set(reconstructed_dto.allowed_actions) == set(original_dto.allowed_actions)

