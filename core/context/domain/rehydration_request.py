from dataclasses import dataclass


@dataclass(frozen=True)
class RehydrationRequest:
    case_id: str
    roles: list[str]  # e.g., ["architect","developer","devops","qa","data"]
    include_timeline: bool = True
    timeline_events: int = 100
    include_summaries: bool = True
    persist_handoff_bundle: bool = True
    ttl_seconds: int = 7 * 24 * 3600
