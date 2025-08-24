import os
import json
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

import asyncio

from neo4j import AsyncGraphDatabase
import redis.asyncio as redis


class Storage:
    def __init__(self) -> None:
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

        self._redis: Optional[redis.Redis] = None
        self._neo4j_driver = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        async with self._lock:
            if self._redis is None:
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
            if self._neo4j_driver is None:
                self._neo4j_driver = AsyncGraphDatabase.driver(
                    self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password)
                )

    async def close(self) -> None:
        async with self._lock:
            if self._redis is not None:
                await self._redis.aclose()
                self._redis = None
            if self._neo4j_driver is not None:
                await self._neo4j_driver.close()
                self._neo4j_driver = None

    # -----------------------------
    # Redis state (context)
    # -----------------------------
    async def load_state(self) -> Dict[str, Any]:
        await self.connect()
        assert self._redis is not None
        data_backlog = await self._redis.get("state:backlog")
        data_messages = await self._redis.get("state:messages")
        backlog: Dict[str, Any] = json.loads(data_backlog) if data_backlog else {}
        messages: List[Dict[str, Any]] = json.loads(data_messages) if data_messages else []
        return {"backlog": backlog, "messages": messages}

    async def save_backlog(self, backlog: Dict[str, Any]) -> None:
        await self.connect()
        assert self._redis is not None
        await self._redis.set("state:backlog", json.dumps(backlog))

    async def save_messages(self, messages: List[Dict[str, Any]]) -> None:
        await self.connect()
        assert self._redis is not None
        # keep a rolling window
        window = messages[-500:]
        await self._redis.set("state:messages", json.dumps(window))

    # -----------------------------
    # Neo4j decisions graph
    # -----------------------------
    async def log_decision(self, *, role: str, sender: str, action: str, task_id: Optional[str], task_title: Optional[str], epic: Optional[str], timestamp: Optional[str] = None) -> None:
        await self.connect()
        assert self._neo4j_driver is not None
        ts = timestamp or datetime.utcnow().isoformat() + "Z"
        decision_id = str(uuid.uuid4())
        cypher = """
        MERGE (u:User {role: $role, name: $sender})
        MERGE (d:Decision {id: $decision_id})
          SET d.action = $action, d.timestamp = $timestamp
        MERGE (u)-[:PERFORMED]->(d)
        WITH d
        FOREACH (_ IN CASE WHEN $task_id IS NULL THEN [] ELSE [1] END |
          MERGE (t:Task {id: $task_id})
            SET t.title = $task_title
          MERGE (d)-[:ON_TASK]->(t)
        )
        WITH d
        FOREACH (_ IN CASE WHEN $epic IS NULL THEN [] ELSE [1] END |
          MERGE (e:Epic {name: $epic})
          WITH d, e
          OPTIONAL MATCH (d)-[:ON_TASK]->(t)
          FOREACH (__ IN CASE WHEN t IS NULL THEN [] ELSE [1] END |
            MERGE (t)-[:BELONGS_TO]->(e)
          )
        )
        """
        async with self._neo4j_driver.session() as session:
            await session.run(
                cypher,
                role=role,
                sender=sender,
                decision_id=decision_id,
                action=action,
                task_id=task_id,
                task_title=task_title,
                epic=epic,
                timestamp=ts,
            )

    async def report_tasks_by_epic(self, epic: str) -> List[Dict[str, Any]]:
        await self.connect()
        assert self._neo4j_driver is not None
        cypher = """
        MATCH (e:Epic {name: $epic})<-[:BELONGS_TO]-(t:Task)
        OPTIONAL MATCH (d:Decision)-[:ON_TASK]->(t)
        WITH t, collect({id: d.id, action: d.action, timestamp: d.timestamp}) AS decisions
        RETURN t.id AS id, t.title AS title, decisions
        ORDER BY title
        """
        results: List[Dict[str, Any]] = []
        async with self._neo4j_driver.session() as session:
            async for rec in await session.run(cypher, epic=epic):
                results.append({
                    "id": rec["id"],
                    "title": rec["title"],
                    "decisions": rec["decisions"],
                })
        return results

    async def report_user_history_by_epic(self, epic: str) -> List[Dict[str, Any]]:
        await self.connect()
        assert self._neo4j_driver is not None
        cypher = """
        MATCH (e:Epic {name: $epic})
        MATCH (u:User)-[:PERFORMED]->(d:Decision)
        OPTIONAL MATCH (d)-[:ON_TASK]->(t:Task)-[:BELONGS_TO]->(e)
        WHERE t IS NOT NULL
        RETURN u.name AS name, u.role AS role,
               collect({decision: d.action, taskId: t.id, taskTitle: t.title, timestamp: d.timestamp}) AS actions
        ORDER BY name
        """
        results: List[Dict[str, Any]] = []
        async with self._neo4j_driver.session() as session:
            async for rec in await session.run(cypher, epic=epic):
                results.append({
                    "name": rec["name"],
                    "role": rec["role"],
                    "actions": rec["actions"],
                })
        return results

    # LLM calls/responses in Redis Streams
    async def _stream_key(self, session_id: str, task_id: Optional[str]) -> str:
        if task_id:
            return f"ctx:{session_id}:{task_id}"
        return f"ctx:{session_id}:_global"

    async def save_llm_call(self, *, session_id: str, task_id: Optional[str], requester: str, content: str, meta: Dict[str, Any]) -> str:
        await self.connect()
        assert self._redis is not None
        key = await self._stream_key(session_id, task_id)
        fields = {
            "type": "call",
            "requester": requester,
            "content": content,
            "meta": json.dumps(meta or {}),
            "ts": datetime.utcnow().isoformat() + "Z",
        }
        entry_id = await self._redis.xadd(key, fields, maxlen=1000, approximate=True)
        await self._redis.expire(key, int(os.getenv("CTX_TTL_SECONDS", "604800")))
        return entry_id

    async def save_llm_response(self, *, session_id: str, task_id: Optional[str], responder: str, content: str, meta: Dict[str, Any]) -> str:
        await self.connect()
        assert self._redis is not None
        key = await self._stream_key(session_id, task_id)
        fields = {
            "type": "response",
            "responder": responder,
            "content": content,
            "meta": json.dumps(meta or {}),
            "ts": datetime.utcnow().isoformat() + "Z",
        }
        entry_id = await self._redis.xadd(key, fields, maxlen=1000, approximate=True)
        await self._redis.expire(key, int(os.getenv("CTX_TTL_SECONDS", "604800")))
        return entry_id

    async def get_context_window(self, *, session_id: str, task_id: Optional[str], max_chars: int = 4000) -> List[Dict[str, Any]]:
        await self.connect()
        assert self._redis is not None
        key = await self._stream_key(session_id, task_id)
        entries = await self._redis.xrevrange(key, count=200)
        out: List[Dict[str, Any]] = []
        total = 0
        for entry_id, fields in entries:
            content = fields.get("content", "")
            length = len(content)
            if total + length > max_chars and out:
                break
            total += length
            record = {"id": entry_id}
            record.update({k: fields.get(k) for k in ["type", "requester", "responder", "content", "ts"]})
            meta_raw = fields.get("meta")
            try:
                record["meta"] = json.loads(meta_raw) if meta_raw else {}
            except Exception:
                record["meta"] = {}
            out.append(record)
        return list(reversed(out))

    async def get_task_decisions(self, task_id: str) -> List[Dict[str, Any]]:
        await self.connect()
        assert self._neo4j_driver is not None
        cypher = """
        MATCH (u:User)-[:PERFORMED]->(d:Decision)-[:ON_TASK]->(t:Task {id: $task_id})
        RETURN u.name AS name, u.role AS role, d.action AS action, d.timestamp AS timestamp
        ORDER BY timestamp
        """
        results: List[Dict[str, Any]] = []
        async with self._neo4j_driver.session() as session:
            async for rec in await session.run(cypher, task_id=task_id):
                results.append({
                    "name": rec["name"],
                    "role": rec["role"],
                    "action": rec["action"],
                    "timestamp": rec["timestamp"],
                })
        return results