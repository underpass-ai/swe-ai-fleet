"""Mapper for StreamMessage entity."""
from services.monitoring.infrastructure.dto import StreamMessageDTO
from services.monitoring.domain.entities import StreamMessage


class StreamMessageMapper:
    """Maps StreamMessageDTO to StreamMessage domain entity."""
    
    @staticmethod
    def to_domain(dto: StreamMessageDTO) -> StreamMessage:
        """Convert DTO to domain entity."""
        return StreamMessage.create(
            subject=dto.subject,
            data=dto.data,
            sequence=dto.sequence,
            timestamp=dto.timestamp,
        )
    
    @staticmethod
    def to_dto(entity: StreamMessage) -> StreamMessageDTO:
        """Convert domain entity to DTO."""
        return StreamMessageDTO(
            subject=entity.subject,
            data=entity.data,
            sequence=entity.sequence,
            timestamp=entity.timestamp,
        )
