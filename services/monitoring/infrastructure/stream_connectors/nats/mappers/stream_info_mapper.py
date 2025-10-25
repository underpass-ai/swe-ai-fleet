"""Mapper for StreamInfo entity."""
from services.monitoring.domain.entities import StreamInfo
from services.monitoring.infrastructure.stream_connectors.nats.dto import StreamInfoDTO


class StreamInfoMapper:
    """Maps StreamInfoDTO to StreamInfo domain entity."""
    
    @staticmethod
    def to_domain(dto: StreamInfoDTO) -> StreamInfo:
        """Convert DTO to domain entity."""
        return StreamInfo.create(
            name=dto.name,
            subjects=dto.subjects,
            messages=dto.messages,
            bytes=dto.bytes,
            first_seq=dto.first_seq,
            last_seq=dto.last_seq,
            consumer_count=dto.consumer_count,
        )
    
    @staticmethod
    def to_dto(entity: StreamInfo) -> StreamInfoDTO:
        """Convert domain entity to DTO."""
        return StreamInfoDTO(
            name=entity.name,
            subjects=entity.subjects,
            messages=entity.messages,
            bytes=entity.bytes,
            first_seq=entity.first_seq,
            last_seq=entity.last_seq,
            consumer_count=entity.consumer_count,
        )
