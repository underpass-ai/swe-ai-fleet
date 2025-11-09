"""DTO for planning.story.transitioned event (external contract)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StoryTransitionedDTO:
    """DTO representing planning.story.transitioned event from Planning Service.

    This DTO lives in INFRASTRUCTURE because it represents the external
    contract (NATS event from another bounded context).
    """

    story_id: str
    from_phase: str
    to_phase: str
    timestamp: str

