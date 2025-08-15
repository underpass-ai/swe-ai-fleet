from typing import Any

import pytest

pytestmark = pytest.mark.e2e


def test_save_to_redis_e2e():
    from swe_ai_fleet.memory.redis_store import LlmCallDTO, RedisStoreImpl

    store = RedisStoreImpl(
        url="redis://:swefleet-dev@localhost:6379/0",
    )

    dto = LlmCallDTO(
        session_id="test",
        task_id="test",
        requester="test",
        model="test",
        params={"test": "test"},
        content="test",
    )

    store.save_llm_call(dto)
    events: list[dict[str, Any]] = store.get_recent_events("test", 1)
    print(events)
    assert len(events) == 1


test_save_to_redis_e2e()
