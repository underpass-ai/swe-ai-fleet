"""Mappers between DTOs and Domain Entities."""
from services.monitoring.infrastructure.dto import (
    StreamInfoDTO,
    StreamMessageDTO,
    MessagesCollectionDTO,
)
from services.monitoring.domain.entities import (
    StreamInfo,
    StreamMessage,
    MessagesCollection,
)


class StreamInfoMapper:
    """Maps StreamInfoDTO to StreamInfo domain entity."""
    
    @staticmethod
    def to_domain(dto: StreamInfoDTO) -> StreamInfo:
        """Convert DTO to domain entity.
        
        Args:
            dto: StreamInfoDTO from NATS adapter
            
        Returns:
            StreamInfo domain entity
        """
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
        """Convert domain entity to DTO.
        
        Args:
            entity: StreamInfo domain entity
            
        Returns:
            StreamInfoDTO for transport
        """
        return StreamInfoDTO(
            name=entity.name,
            subjects=entity.subjects,
            messages=entity.messages,
            bytes=entity.bytes,
            first_seq=entity.first_seq,
            last_seq=entity.last_seq,
            consumer_count=entity.consumer_count,
        )


class StreamMessageMapper:
    """Maps StreamMessageDTO to StreamMessage domain entity."""
    
    @staticmethod
    def to_domain(dto: StreamMessageDTO) -> StreamMessage:
        """Convert DTO to domain entity.
        
        Args:
            dto: StreamMessageDTO from NATS adapter
            
        Returns:
            StreamMessage domain entity
        """
        return StreamMessage.create(
            subject=dto.subject,
            data=dto.data,
            sequence=dto.sequence,
            timestamp=dto.timestamp,
        )
    
    @staticmethod
    def to_dto(entity: StreamMessage) -> StreamMessageDTO:
        """Convert domain entity to DTO.
        
        Args:
            entity: StreamMessage domain entity
            
        Returns:
            StreamMessageDTO for transport
        """
        return StreamMessageDTO(
            subject=entity.subject,
            data=entity.data,
            sequence=entity.sequence,
            timestamp=entity.timestamp,
        )


class MessagesCollectionMapper:
    """Maps MessagesCollectionDTO to MessagesCollection domain entity."""
    
    @staticmethod
    def to_domain(dto: MessagesCollectionDTO) -> MessagesCollection:
        """Convert DTO to domain entity.
        
        Args:
            dto: MessagesCollectionDTO from NATS adapter
            
        Returns:
            MessagesCollection domain entity
        """
        messages = [
            StreamMessageMapper.to_domain(msg_dto)
            for msg_dto in dto.messages
        ]
        return MessagesCollection.create(messages=messages)
    
    @staticmethod
    def to_dto(entity: MessagesCollection) -> MessagesCollectionDTO:
        """Convert domain entity to DTO.
        
        Args:
            entity: MessagesCollection domain entity
            
        Returns:
            MessagesCollectionDTO for transport
        """
        message_dtos = [
            StreamMessageMapper.to_dto(msg)
            for msg in entity.messages
        ]
        return MessagesCollectionDTO(messages=message_dtos)


__all__ = [
    "StreamInfoMapper",
    "StreamMessageMapper",
    "MessagesCollectionMapper",
]
