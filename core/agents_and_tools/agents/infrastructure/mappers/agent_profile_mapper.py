"""Mapper for converting between AgentProfile domain entity and AgentProfileDTO."""

from core.agents_and_tools.agents.domain.entities.agent_profile import AgentProfile
from core.agents_and_tools.agents.infrastructure.dtos.agent_profile_dto import AgentProfileDTO


class AgentProfileMapper:
    """Mapper for converting between AgentProfile DTO and Entity."""

    def dto_to_entity(self, dto: AgentProfileDTO) -> AgentProfile:
        """Convert DTO to domain entity."""
        return AgentProfile(
            name=dto.name,
            model=dto.model,
            context_window=dto.context_window,
            temperature=dto.temperature,
            max_tokens=dto.max_tokens,
        )

    def entity_to_dto(self, entity: AgentProfile) -> AgentProfileDTO:
        """Convert domain entity to DTO."""
        return AgentProfileDTO(
            name=entity.name,
            model=entity.model,
            context_window=entity.context_window,
            temperature=entity.temperature,
            max_tokens=entity.max_tokens,
        )

