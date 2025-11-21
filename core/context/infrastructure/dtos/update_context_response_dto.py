"""DTO for UpdateContext response (NATS message contract)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateContextResponseDTO:
    """DTO representing UpdateContext response for NATS messaging.

    This DTO lives in INFRASTRUCTURE because it represents the external
    contract (NATS message to other services).

    NO business validation here. Just data structure.
    """

    story_id: str
    status: str
    version: int
    hash: str
    warnings: list[str]

