"""Mapper for converting between Role domain entity and RoleDTO."""

from core.agents_and_tools.agents.domain.entities.rbac import Action, ActionEnum, Role, RoleEnum, ScopeEnum
from core.agents_and_tools.agents.infrastructure.dtos.role_dto import RoleDTO


class RoleMapper:
    """Mapper for converting between Role DTO and Entity.

    Following hexagonal architecture, this mapper lives in infrastructure layer
    and handles conversions between domain entities and DTOs for serialization.

    No reflection, no dynamic attribute access - explicit mapping only.
    """

    @staticmethod
    def dto_to_entity(dto: RoleDTO) -> Role:
        """Convert DTO to domain entity.

        Args:
            dto: RoleDTO with string values

        Returns:
            Role domain entity with enums

        Raises:
            ValueError: If role name or scope is invalid

        Examples:
            >>> dto = RoleDTO(
            ...     name="architect",
            ...     scope="technical",
            ...     allowed_actions=["approve_design", "reject_design"]
            ... )
            >>> role = RoleMapper.dto_to_entity(dto)
            >>> role.value == RoleEnum.ARCHITECT
            True
        """
        # Convert name string to RoleEnum
        try:
            role_enum = RoleEnum(dto.name.lower())
        except ValueError as e:
            raise ValueError(f"Invalid role name: {dto.name}") from e

        # Convert scope string to ScopeEnum
        try:
            scope_enum = ScopeEnum(dto.scope.lower())
        except ValueError as e:
            raise ValueError(f"Invalid scope: {dto.scope}") from e

        # Convert action strings to ActionEnum frozenset
        action_enums: set[ActionEnum] = set()
        for action_name in dto.allowed_actions:
            try:
                action_enum = ActionEnum(action_name.lower())
                action_enums.add(action_enum)
            except ValueError as e:
                raise ValueError(f"Invalid action name: {action_name}") from e

        return Role(
            value=role_enum,
            allowed_actions=frozenset(action_enums),
            scope=scope_enum,
        )

    @staticmethod
    def entity_to_dto(entity: Role) -> RoleDTO:
        """Convert domain entity to DTO.

        Args:
            entity: Role domain entity

        Returns:
            RoleDTO with string values for serialization

        Examples:
            >>> role = Role(
            ...     value=RoleEnum.ARCHITECT,
            ...     allowed_actions=frozenset([ActionEnum.APPROVE_DESIGN]),
            ...     scope=ScopeEnum.TECHNICAL
            ... )
            >>> dto = RoleMapper.entity_to_dto(role)
            >>> dto.name
            'architect'
        """
        return RoleDTO(
            name=entity.value.value,
            scope=entity.scope.value,
            allowed_actions=[action.value for action in entity.allowed_actions],
        )

