"""Tests for infrastructure mappers."""

import pytest
from services.monitoring.infrastructure.dto import (
    StreamInfoDTO,
    StreamMessageDTO,
    MessagesCollectionDTO,
)
from services.monitoring.infrastructure.mappers import (
    StreamInfoMapper,
    StreamMessageMapper,
    MessagesCollectionMapper,
)
from services.monitoring.domain.entities import (
    StreamInfo,
    StreamMessage,
    MessagesCollection,
)


class TestStreamInfoMapper:
    """Test suite for StreamInfoMapper."""
    
    def test_to_domain(self):
        """Test converting DTO to domain entity."""
        dto = StreamInfoDTO(
            name="orders",
            subjects=["orders.>"],
            messages=100,
            bytes=50000,
            first_seq=1,
            last_seq=100,
            consumer_count=2,
        )
        
        entity = StreamInfoMapper.to_domain(dto)
        
        assert isinstance(entity, StreamInfo)
        assert entity.name == "orders"
        assert entity.messages == 100
    
    def test_to_dto(self):
        """Test converting domain entity to DTO."""
        entity = StreamInfo.create(
            name="orders",
            subjects=["orders.>"],
            messages=100,
            bytes=50000,
            first_seq=1,
            last_seq=100,
            consumer_count=2,
        )
        
        dto = StreamInfoMapper.to_dto(entity)
        
        assert isinstance(dto, StreamInfoDTO)
        assert dto.name == "orders"
        assert dto.messages == 100
    
    def test_roundtrip(self):
        """Test roundtrip: entity → DTO → entity."""
        original = StreamInfo.create(
            name="payments",
            subjects=["payments.>"],
            messages=50,
            bytes=25000,
            first_seq=1,
            last_seq=50,
            consumer_count=1,
        )
        
        dto = StreamInfoMapper.to_dto(original)
        restored = StreamInfoMapper.to_domain(dto)
        
        assert original.name == restored.name
        assert original.messages == restored.messages


class TestStreamMessageMapper:
    """Test suite for StreamMessageMapper."""
    
    def test_to_domain(self):
        """Test converting DTO to domain entity."""
        dto = StreamMessageDTO(
            subject="orders.created",
            data={"order_id": 123},
            sequence=42,
            timestamp="2025-10-25T10:00:00Z",
        )
        
        entity = StreamMessageMapper.to_domain(dto)
        
        assert isinstance(entity, StreamMessage)
        assert entity.subject == "orders.created"
        assert entity.sequence == 42
    
    def test_to_dto(self):
        """Test converting domain entity to DTO."""
        entity = StreamMessage.create(
            subject="orders.created",
            data={"order_id": 123},
            sequence=42,
            timestamp="2025-10-25T10:00:00Z",
        )
        
        dto = StreamMessageMapper.to_dto(entity)
        
        assert isinstance(dto, StreamMessageDTO)
        assert dto.subject == "orders.created"
        assert dto.sequence == 42


class TestMessagesCollectionMapper:
    """Test suite for MessagesCollectionMapper."""
    
    def test_to_domain(self):
        """Test converting DTO to domain entity."""
        msg_dto1 = StreamMessageDTO(
            subject="orders.created",
            data={"id": 1},
            sequence=1,
            timestamp="2025-10-25T10:00:00Z",
        )
        msg_dto2 = StreamMessageDTO(
            subject="orders.updated",
            data={"id": 2},
            sequence=2,
            timestamp="2025-10-25T10:01:00Z",
        )
        dto = MessagesCollectionDTO(messages=[msg_dto1, msg_dto2])
        
        entity = MessagesCollectionMapper.to_domain(dto)
        
        assert isinstance(entity, MessagesCollection)
        assert entity.count() == 2
        assert entity.messages[0].subject == "orders.created"
    
    def test_to_dto(self):
        """Test converting domain entity to DTO."""
        msg1 = StreamMessage.create(
            subject="orders.created",
            data={"id": 1},
            sequence=1,
            timestamp="2025-10-25T10:00:00Z",
        )
        msg2 = StreamMessage.create(
            subject="orders.updated",
            data={"id": 2},
            sequence=2,
            timestamp="2025-10-25T10:01:00Z",
        )
        entity = MessagesCollection.create(messages=[msg1, msg2])
        
        dto = MessagesCollectionMapper.to_dto(entity)
        
        assert isinstance(dto, MessagesCollectionDTO)
        assert len(dto.messages) == 2
        assert dto.messages[0].subject == "orders.created"
    
    def test_roundtrip(self):
        """Test roundtrip: entity → DTO → entity."""
        msg = StreamMessage.create(
            subject="test",
            data={"test": True},
            sequence=5,
            timestamp="2025-10-25T10:00:00Z",
        )
        original = MessagesCollection.create(messages=[msg])
        
        dto = MessagesCollectionMapper.to_dto(original)
        restored = MessagesCollectionMapper.to_domain(dto)
        
        assert original.count() == restored.count()
        assert original.messages[0].subject == restored.messages[0].subject
