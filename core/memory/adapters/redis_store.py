"""Redis-backed store for LLM session events using Redis Streams and TTLs."""

from __future__ import annotations

import json
import time
from typing import Any

import redis
from core.memory.dtos.llm_call_dto import LlmCallDTO
from core.memory.dtos.llm_response_dto import LlmResponseDTO
from core.memory.ports.persistence_store_port import PersistenceStorePort

# Encodable value type for redis-py XADD fields (matches stubs)
# https://redis.io/docs/latest/develop/clients/redis-py/
EncVal = str | int | float | bytes | bytearray | memoryview

# ---------- Implementation (Streams + TTL) ----------


class RedisStoreImpl(PersistenceStorePort):
    """
    Stream per session:
      key: swe:session:{session_id}:stream
      entry fields for llm_call / llm_response
    Per-session metadata:
      key: swe:session:{session_id}:meta  (hash)
    """

    def __init__(self, url: str, default_ttl_sec: int = 7 * 24 * 3600, stream_maxlen: int = 5000) -> None:
        # decode_responses=True gives str instead of bytes for convenience.
        self.client = redis.Redis.from_url(url, decode_responses=True)
        self.ttl = int(default_ttl_sec)
        self.maxlen = int(stream_maxlen)

    # ---- Key helpers

    @staticmethod
    def _k_stream(session_id: str) -> str:
        return f"swe:session:{session_id}:stream"

    @staticmethod
    def _k_meta(session_id: str) -> str:
        return f"swe:session:{session_id}:meta"

    # ---- Internal

    def _ensure_session_ttl(self, session_id: str) -> None:
        # Set TTL only if not already set (NX)
        # to avoid shortening an existing expiry.
        # https://redis.io/docs/latest/commands/expire/
        self.client.expire(self._k_meta(session_id), self.ttl, nx=True)
        self.client.expire(self._k_stream(session_id), self.ttl, nx=True)

    # ---- Public API

    def set_session_meta(self, session_id: str, meta: dict[str, str]) -> None:
        """Set or update session metadata and ensure TTLs.

        Common fields: created_at, case_id, task_id, role
        """
        if not isinstance(meta, dict):
            raise ValueError("meta must be a dict of str->str")
        # Initialize created_at if missing
        now_ms = str(int(time.time() * 1000))
        if "created_at" not in meta:
            meta = {**meta, "created_at": now_ms}
        self.client.hset(self._k_meta(session_id), mapping=meta)
        self._ensure_session_ttl(session_id)

    def tag_session_with_case(self, session_id: str, case_id: str) -> None:
        """Convenience wrapper to attach case_id to a session meta."""
        self.set_session_meta(session_id, {"case_id": case_id})

    def save_llm_call(self, dto: LlmCallDTO) -> str:
        now_ms = str(int(time.time() * 1000))
        fields: dict[str, EncVal] = {
            "type": "llm_call",
            "task_id": dto.task_id,
            "requester": dto.requester,
            "model": dto.model,
            "params": json.dumps(dto.params),
            "content": dto.content,
            "parent_msg_id": dto.parent_msg_id or "",
            "ts": now_ms,
        }
        # XADD with approximate MAXLEN trimming for efficiency.
        # https://redis.io/docs/latest/commands/xadd/
        msg_id = self.client.xadd(
            self._k_stream(dto.session_id),
            fields,
            maxlen=self.maxlen,
            approximate=True,
        )

        # Initialize meta if first time and set TTLs.
        self.client.hsetnx(self._k_meta(dto.session_id), "created_at", now_ms)
        self._ensure_session_ttl(dto.session_id)
        return msg_id

    def save_llm_response(self, dto: LlmResponseDTO) -> str:
        now_ms = str(int(time.time() * 1000))
        fields: dict[str, EncVal] = {
            "type": "llm_response",
            "task_id": dto.task_id,
            "responder": dto.responder,
            "model": dto.model,
            "content": dto.content,
            "usage": json.dumps(dto.usage),
            "parent_msg_id": dto.parent_msg_id or "",
            "ts": now_ms,
        }
        msg_id = self.client.xadd(
            self._k_stream(dto.session_id),
            fields,
            maxlen=self.maxlen,
            approximate=True,
        )
        self._ensure_session_ttl(dto.session_id)
        return msg_id

    def get_recent_events(
        self,
        session_id: str,
        count: int = 100,
    ) -> list[dict[str, Any]]:
        # XRANGE gives an ordered slice.
        # XREVRANGE is also available if you prefer newest-first.
        # https://redis.io/docs/latest/commands/xrange/
        stream = self._k_stream(session_id)
        # Use XREVRANGE for performance (grab newest N),
        # then reverse to oldest..newest.
        entries = self.client.xrevrange(stream, count=count)
        out: list[dict[str, Any]] = []
        for msg_id, kv in reversed(entries):
            record = {"id": msg_id}
            record.update(kv)
            out.append(record)
        return out

    def get_context_window(
        self,
        session_id: str,
        max_chars: int = 12000,
    ) -> str:
        # Simple folding of the last events into a context string.
        events = self.get_recent_events(session_id, count=200)
        acc: list[str] = []
        size = 0
        for e in events:
            line = f"[{e.get('type')}] {e.get('model', '-')} :: {e.get('content', '')}\n"
            if size + len(line) > max_chars:
                break
            acc.append(line)
            size += len(line)
        return "".join(acc)
