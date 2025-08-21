from dataclasses import dataclass


@dataclass(frozen=True)
class ReportRequest:
    case_id: str
    max_events: int = 200
    include_constraints: bool = True
    include_acceptance: bool = True
    include_timeline: bool = True
    include_dependencies: bool = True  # from subtasks.depends_on
    persist_to_redis: bool = True
    ttl_seconds: int = 14 * 24 * 3600
