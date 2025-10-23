from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.tools.adapters.redis_event_bus import RedisEventBus
from core.tools.ports.event_bus_port import EventRecord


def test_publish_event_ok():
    with patch("redis.Redis") as redis_cls:
        mock_client = MagicMock()
        redis_cls.from_url.return_value = mock_client
        bus = RedisEventBus("redis://localhost:6379/0")
        evt = EventRecord(topic="demo", key="k1", payload={"x": 1})
        mock_client.xadd.return_value = "1670000000-0"

        mid = bus.publish(evt)
        assert mid == "1670000000-0"
        mock_client.xadd.assert_called_once()


