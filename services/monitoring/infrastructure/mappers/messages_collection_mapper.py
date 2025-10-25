"""Mapper for MessagesCollection entity."""
from services.monitoring.infrastructure.dto import MessagesCollectionDTO
from services.monitoring.domain.entities import MessagesCollection
from .stream_message_mapper import StreamMessageMapper


class MessagesCollectionMapper:
    """Maps MessagesCollectionDTO to MessagesCollection domain entity."""
    
    @staticmethod
    def to_domain(dto: MessagesCollectionDTO) -> MessagesCollection:
        """Convert DTO to domain entity."""
        messages = [
            StreamMessageMapper.to_domain(msg_dto)
            for msg_dto in dto.messages
        ]
        return MessagesCollection.create(messages=messages)
    
    @staticmethod
    def to_dto(entity: MessagesCollection) -> MessagesCollectionDTO:
        """Convert domain entity to DTO."""
        message_dtos = [
            StreamMessageMapper.to_dto(msg)
            for msg in entity.messages
        ]
        return MessagesCollectionDTO(messages=message_dtos)
