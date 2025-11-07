"""Mapper for StateTransition entity.

Converts domain entities to DTOs and serializable formats.
Following Hexagonal Architecture (infrastructure responsibility).
"""

from typing import Any

from services.workflow.application.dto.state_transition_dto import StateTransitionDTO
from services.workflow.domain.entities.state_transition import StateTransition


class StateTransitionMapper:
    """Maps StateTransition domain entity to DTO and dict.

    This is infrastructure responsibility:
    - Domain entities do NOT know about DTOs or dicts
    - Mappers live in infrastructure layer
    - Handle all conversions (domain → DTO → dict)

    Following DDD:
    - No to_dict() / from_dict() in domain
    - Explicit mappers in infrastructure
    - Type-safe conversions
    """

    @staticmethod
    def to_dto(transition: StateTransition) -> StateTransitionDTO:
        """Convert StateTransition domain entity to DTO.

        Tell, Don't Ask: Use domain methods instead of attribute access.

        Args:
            transition: Domain entity

        Returns:
            StateTransitionDTO (immutable)
        """
        return StateTransitionDTO(
            from_state=transition.from_state,
            to_state=transition.to_state,
            action=transition.get_action_value(),
            actor_role=transition.get_actor_role_value(),
            timestamp=transition.timestamp.isoformat(),
            feedback=transition.feedback,
        )

    @staticmethod
    def to_dict(transition: StateTransition) -> dict[str, Any]:
        """Convert StateTransition domain entity to dict (for Neo4j).

        Convenience method: domain → DTO → dict in one call.

        Args:
            transition: Domain entity

        Returns:
            Dict suitable for Neo4j/Valkey persistence
        """
        dto = StateTransitionMapper.to_dto(transition)

        return {
            "from_state": dto.from_state,
            "to_state": dto.to_state,
            "action": dto.action,
            "actor_role": dto.actor_role,
            "timestamp": dto.timestamp,
            "feedback": dto.feedback,
        }

    @staticmethod
    def to_dict_list(transitions: tuple[StateTransition, ...]) -> list[dict[str, Any]]:
        """Convert tuple of StateTransition to list of dicts.

        Used by Neo4j adapter for batch persistence.

        Args:
            transitions: Tuple of domain entities (immutable history)

        Returns:
            List of dicts suitable for Neo4j
        """
        return [StateTransitionMapper.to_dict(t) for t in transitions]

