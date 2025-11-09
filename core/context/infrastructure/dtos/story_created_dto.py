"""DTO for planning.story.created event (external contract)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StoryCreatedDTO:
    """DTO representing planning.story.created event from Planning Service.

    This DTO lives in INFRASTRUCTURE because it represents the external
    contract (NATS event from another bounded context).
    """

    story_id: str
    epic_id: str
    name: str

