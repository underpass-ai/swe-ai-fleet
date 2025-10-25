"""Messages Collection Data Transfer Object."""
from dataclasses import dataclass
from typing import Sequence

from .stream_message_dto import StreamMessageDTO


@dataclass
class MessagesCollectionDTO:
    """DTO for a collection of messages from NATS."""
    messages: Sequence[StreamMessageDTO]
