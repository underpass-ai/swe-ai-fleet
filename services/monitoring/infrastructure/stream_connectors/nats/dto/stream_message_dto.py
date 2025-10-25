"""Stream Message Data Transfer Object."""
from dataclasses import dataclass
from typing import Any


@dataclass
class StreamMessageDTO:
    """DTO for a message from NATS stream."""
    subject: str
    data: dict[str, Any]
    sequence: int
    timestamp: str
