"""Stream Info Data Transfer Object."""
from collections.abc import Sequence
from dataclasses import dataclass


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
