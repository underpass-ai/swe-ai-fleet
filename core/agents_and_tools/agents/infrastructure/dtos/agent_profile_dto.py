"""Data Transfer Object for AgentProfile in infrastructure layer."""

from dataclasses import dataclass


@dataclass
class AgentProfileDTO:
    """DTO for agent profile configuration.

    Used for serialization/deserialization between layers.
    All fields are required.

    DTOs should NOT have to_dict() or from_dict() methods.
    Use mappers to convert between DTOs and domain entities.
    Initialization from dictionaries is a bad practice.
    """

    name: str
    model: str
    context_window: int
    temperature: float
    max_tokens: int

