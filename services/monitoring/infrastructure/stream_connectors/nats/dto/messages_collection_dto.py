"""Messages Collection Data Transfer Object."""
from collections.abc import Sequence
from dataclasses import dataclass

from .stream_message_dto import StreamMessageDTO


@dataclass
class MessagesCollectionDTO:
    """DTO for a collection of messages from NATS."""
    messages: Sequence[StreamMessageDTO]
