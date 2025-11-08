import json
import time
from typing import Any, cast

from core.memory.ports.persistence_kv_port import PersistenceKvPort

# Use domain entities
from core.context.domain.story_spec import StorySpec
from core.context.domain.plan_version import PlanVersion
from core.context.domain.planning_event import PlanningEvent
from core.context.domain.task_plan import TaskPlan

# Use mappers for conversions
from core.context.infrastructure.mappers.story_spec_mapper import StorySpecMapper
from core.context.infrastructure.mappers.plan_version_mapper import PlanVersionMapper
from core.context.infrastructure.mappers.planning_event_mapper import PlanningEventMapper
from core.context.infrastructure.mappers.task_plan_mapper import TaskPlanMapper

from ..ports.planning_read_port import PlanningReadPort


class RedisPlanningReadAdapter(PlanningReadPort):
    def __init__(self, client: PersistenceKvPort) -> None:
        self.r = client

    @property
    def client(self) -> PersistenceKvPort:
        """Expose the underlying Redis client for direct operations."""
        return self.r

    @staticmethod
    def _k_spec(case_id: str) -> str:
        return f"swe:case:{case_id}:spec"

    @staticmethod
    def _k_draft(case_id: str) -> str:
        return f"swe:case:{case_id}:planning:draft"

    @staticmethod
    def _k_stream(case_id: str) -> str:
        return f"swe:case:{case_id}:planning:stream"

    @staticmethod
    def _k_summary_last(case_id: str, role: str | None = None) -> str:
        """Generate cache key for last summary.

        Args:
            case_id: Story identifier
            role: Optional role for RBAC L3 cache isolation

        Returns:
            Cache key string
        """
        if role:
            return f"swe:case:{case_id}:role:{role}:summaries:last"
        return f"swe:case:{case_id}:summaries:last"  # Backward compatibility

    @staticmethod
    def _k_handoff(case_id: str, ts: int, role: str | None = None) -> str:
        """Generate cache key for handoff bundle.

        Args:
            case_id: Story identifier
            ts: Timestamp
            role: Optional role for RBAC L3 cache isolation

        Returns:
            Cache key string

        RBAC L3: Includes role in key to prevent cache poisoning across roles.
        Different roles should never share cached context bundles.
        """
        if role:
            return f"swe:case:{case_id}:role:{role}:handoff:{ts}"
        return f"swe:case:{case_id}:handoff:{ts}"  # Backward compatibility

    def get_case_spec(self, case_id: str) -> StorySpec | None:
        """Get story specification from Redis.

        Args:
            case_id: Story identifier (legacy parameter name)

        Returns:
            StorySpec domain entity or None if not found
        """
        raw = self.r.get(self._k_spec(case_id))
        if not raw:
            return None

        text = cast(str, raw)
        data = json.loads(text)

        # Use mapper to convert Redis data to domain entity
        return StorySpecMapper.from_redis_data(data)

    def get_plan_draft(self, case_id: str) -> PlanVersion | None:
        """Get draft plan from Redis.

        Args:
            case_id: Story identifier (legacy parameter name)

        Returns:
            PlanVersion domain entity or None if not found
        """
        raw = self.r.get(self._k_draft(case_id))
        if not raw:
            return None

        text = cast(str, raw)
        data = json.loads(text)

        # Use mapper to convert Redis data to domain entity
        return PlanVersionMapper.from_redis_data(data)

    def get_planning_events(self, case_id: str, count: int = 200) -> list[PlanningEvent]:
        """Get planning events from Redis stream.

        Args:
            case_id: Story identifier (legacy parameter name)
            count: Max number of events to return

        Returns:
            List of PlanningEvent domain entities
        """
        # Read from Redis stream (chronological order)
        entries_raw: Any = self.r.xrevrange(self._k_stream(case_id), count=count)
        entries = list(cast(list[tuple[str, dict[str, Any]]], entries_raw))

        # Sort by timestamp to normalize order
        entries.sort(key=lambda item: int(item[1].get("ts", "0")))

        events: list[PlanningEvent] = []
        for msg_id, fields in entries:
            # Parse payload JSON
            try:
                payload_text = fields.get("payload", "{}")
                payload = json.loads(payload_text)
            except json.JSONDecodeError:
                payload = {"raw": fields.get("payload", "")}

            # Build data dict for mapper
            event_data = {
                "id": msg_id,
                "event": fields.get("event", ""),
                "actor": fields.get("actor", ""),
                "payload": payload,
                "ts_ms": int(fields.get("ts", "0")),
            }

            # Use mapper to convert to domain entity
            events.append(PlanningEventMapper.from_redis_data(event_data))

        return events

    def read_last_summary(self, case_id: str, role: str | None = None) -> str | None:
        """Read last summary from cache.

        Args:
            case_id: Story identifier
            role: Optional role for RBAC L3 cache isolation

        Returns:
            Summary text or None
        """
        raw = self.r.get(self._k_summary_last(case_id, role=role))
        return cast(str | None, raw if raw else None)

    def save_handoff_bundle(
        self,
        case_id: str,
        bundle: dict[str, Any],
        ttl_seconds: int,
        role: str | None = None,
    ) -> None:
        """Save handoff bundle to cache with role isolation.

        Args:
            case_id: Story identifier
            bundle: Handoff bundle data
            ttl_seconds: Time to live in seconds
            role: Optional role for RBAC L3 cache isolation

        RBAC L3: When role is provided, cache key includes role to prevent
        different roles from sharing cached bundles (cache poisoning attack).
        """
        ts = int(time.time() * 1000)
        pipe = self.r.pipeline()
        pipe.set(self._k_handoff(case_id, ts, role=role), json.dumps(bundle), ex=ttl_seconds)
        pipe.execute()
