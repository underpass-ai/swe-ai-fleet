from __future__ import annotations

import json
from typing import Any

import redis
from core.agents_and_tools.tools.ports.event_bus_port import EventBusPort, EventRecord


class RedisEventBus(EventBusPort):
    """Simple Redis Streams-based event bus.

    Topics map to stream keys: swe:bus:<topic>
    """

    def __init__(self, url: str) -> None:
        self._c: redis.Redis = redis.Redis.from_url(url, decode_responses=True)

    @staticmethod
    def _k(topic: str) -> str:
        return f"swe:bus:{topic}"

    def publish(self, event: EventRecord) -> str:
        fields: dict[str, Any] = {
            "key": event.key,
            "payload": json.dumps(event.payload),
        }
        return self._c.xadd(self._k(event.topic), fields, maxlen=5000, approximate=True)


