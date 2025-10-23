from __future__ import annotations

from typing import Any

import pytest

# pyright: reportMissingTypeStubs=false, reportMissingImports=false
# ruff: noqa: ANN401


class FakeRedis:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        self.meta: dict[str, dict[str, Any]] = {}
        self.expire_calls: list[tuple[str, int, bool]] = []
        self._id_counter: int = 0

    # Factory shim to match redis.Redis.from_url
    @classmethod
    def from_url(cls, *_args: Any, **_kwargs: Any) -> FakeRedis:
        return cls()

    def xadd(
        self,
        name: str,
        fields: dict[str, Any],
        *,
        maxlen: int | None = None,
        approximate: bool | None = None,
    ) -> str:  # noqa: ARG002
        _ = approximate
        self._id_counter += 1
        msg_id = f"{self._id_counter}-0"
        self.streams.setdefault(name, []).append((msg_id, dict(fields)))
        # Trim if maxlen set
        if maxlen is not None:
            overflow = len(self.streams[name]) - int(maxlen)
            if overflow > 0:
                self.streams[name] = self.streams[name][overflow:]
        return msg_id

    def xrevrange(
        self,
        name: str,
        *,
        count: int | None = None,
    ) -> list[tuple[str, dict[str, Any]]]:
        items = list(self.streams.get(name, []))
        items.reverse()  # newest-first like real XREVRANGE
        if count is not None:
            items = items[: int(count)]
        return items

    def hsetnx(self, name: str, key: str, value: Any) -> int:
        h = self.meta.setdefault(name, {})
        if key in h:
            return 0
        h[key] = value
        return 1

    # Minimal hset implementation to support mapping=...
    def hset(
        self,
        name: str,
        key: str | None = None,
        value: Any | None = None,
        *,
        mapping: dict[str, Any] | None = None,
    ) -> int:  # noqa: D401
        h = self.meta.setdefault(name, {})
        added = 0
        if mapping is not None:
            for k, v in mapping.items():
                if k not in h:
                    added += 1
                h[k] = v
        elif key is not None:
            if key not in h:
                added = 1
            h[key] = value
        return added

    def expire(
        self,
        name: str,
        ttl: int,
        *,
        nx: bool | None = None,
    ) -> bool:  # noqa: FBT001
        self.expire_calls.append((name, int(ttl), bool(nx)))
        return True


@pytest.fixture(name="fake_redis")
def redis_fake(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    fake = FakeRedis()
    # Patch the redis module used inside the implementation
    import core.memory.adapters.redis_store as redis_store  # type: ignore

    monkeypatch.setattr(redis_store.redis, "Redis", FakeRedis)
    # Ensure from_url returns our single fake instance
    monkeypatch.setattr(
        redis_store.redis.Redis,
        "from_url",
        classmethod(lambda _cls, *_a, **_k: fake),
    )
    return fake


def test_save_llm_call_and_list_events(fake_redis: FakeRedis) -> None:
    _ = fake_redis
    from core.memory.adapters.redis_store import LlmCallDTO, RedisStoreImpl

    store = RedisStoreImpl(url="redis://unused")
    dto = LlmCallDTO(
        session_id="s1",
        task_id="t1",
        requester="user:1",
        model="m",
        params={"temp": 0},
        content="hello",
    )

    msg_id = store.save_llm_call(dto)
    assert isinstance(msg_id, str) and msg_id.endswith("-0")

    events = store.get_recent_events("s1", count=10)
    assert len(events) == 1
    assert events[0]["type"] == "llm_call"
    assert events[0]["content"] == "hello"


def test_save_llm_response_appends_and_order(fake_redis: FakeRedis) -> None:
    _ = fake_redis
    from core.memory.adapters.redis_store import (
        LlmCallDTO,
        LlmResponseDTO,
        RedisStoreImpl,
    )

    store = RedisStoreImpl(url="redis://unused")
    store.save_llm_call(
        LlmCallDTO(
            session_id="s2",
            task_id="t",
            requester="user",
            model="m",
            params={},
            content="prompt",
        )
    )
    store.save_llm_response(
        LlmResponseDTO(
            session_id="s2",
            task_id="t",
            responder="agent",
            model="m",
            content="answer",
            usage={"tokens": 1},
        )
    )

    events = store.get_recent_events("s2", count=10)
    # Oldest to newest
    types = [e["type"] for e in events]
    assert types == ["llm_call", "llm_response"]


def test_get_context_window_truncates(fake_redis: FakeRedis) -> None:
    _ = fake_redis
    from core.memory.adapters.redis_store import LlmCallDTO, RedisStoreImpl

    store = RedisStoreImpl(url="redis://unused")
    for i in range(3):
        store.save_llm_call(
            LlmCallDTO(
                session_id="s3",
                task_id=f"t{i}",
                requester="user",
                model="m",
                params={},
                content=f"line-{i}",
            )
        )

    ctx = store.get_context_window("s3", max_chars=30)
    # Should contain at least the first line, but be truncated overall
    assert "line-0" in ctx
    assert len(ctx) <= 30


def test_ttl_is_set_on_stream_and_meta(fake_redis: FakeRedis) -> None:
    from core.memory.adapters.redis_store import LlmCallDTO, RedisStoreImpl

    store = RedisStoreImpl(url="redis://unused")
    store.save_llm_call(
        LlmCallDTO(
            session_id="s4",
            task_id="t",
            requester="user",
            model="m",
            params={},
            content="c",
        )
    )

    # two expire calls: meta and stream keys
    assert len(fake_redis.expire_calls) >= 2  # ensure TTL set


def test_set_session_meta_and_tag_case(fake_redis: FakeRedis) -> None:
    from core.memory.adapters.redis_store import RedisStoreImpl

    store = RedisStoreImpl(url="redis://unused")
    # set meta without created_at to assert auto-fill and TTLs
    store.set_session_meta("s5", {"role": "dev"})
    assert "created_at" in fake_redis.meta["swe:session:s5:meta"]
    # tag case convenience
    store.tag_session_with_case("s5", "CASE-1")
    assert fake_redis.meta["swe:session:s5:meta"]["case_id"] == "CASE-1"
    # TTLs ensured
    keys = [k for (k, _ttl, _nx) in fake_redis.expire_calls]
    assert "swe:session:s5:meta" in keys
    assert "swe:session:s5:stream" in keys
