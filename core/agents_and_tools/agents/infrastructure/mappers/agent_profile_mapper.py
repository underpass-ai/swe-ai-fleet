"""Mapper for converting between AgentProfile domain entity and AgentProfileDTO."""

from core.agents_and_tools.agents.domain.entities.agent_profile import AgentProfile
from core.agents_and_tools.agents.infrastructure.dtos.agent_profile_dto import AgentProfileDTO


def profile_dto_to_entity(dto: AgentProfileDTO) -> AgentProfile:
    """Convert DTO to domain entity."""
    return AgentProfile(
        name=dto.name,
        model=dto.model,
        context_window=dto.context_window,
        temperature=dto.temperature,
        max_tokens=dto.max_tokens,
    )


def profile_entity_to_dto(entity: AgentProfile) -> AgentProfileDTO:
    """Convert domain entity to DTO."""
    return AgentProfileDTO(
        name=entity.name,
        model=entity.model,
        context_window=entity.context_window,
        temperature=entity.temperature,
        max_tokens=entity.max_tokens,
    )

