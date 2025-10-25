"""Data Transfer Objects from external sources."""
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass
class StreamInfoDTO:
    """DTO for stream information from NATS."""
    name: str
    subjects: Sequence[str]
    messages: int
    bytes: int
    first_seq: int
    last_seq: int
    consumer_count: int


@dataclass
class StreamMessageDTO:
    """DTO for a message from NATS stream."""
    subject: str
    data: dict[str, Any]
    sequence: int
    timestamp: str


@dataclass
class MessagesCollectionDTO:
    """DTO for a collection of messages from NATS."""
    messages: Sequence[StreamMessageDTO]


__all__ = [
    "StreamInfoDTO",
    "StreamMessageDTO",
    "MessagesCollectionDTO",
]
