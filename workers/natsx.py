"""
NATS JetStream wrapper for Python workers.
Provides simple publish/consume patterns with durable consumers and acks.
"""

import asyncio
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import nats
from nats.js import JetStreamContext
from nats.js.api import StreamConfig, RetentionPolicy


@dataclass
class ConnectOptions:
    url: str = "nats://nats:4222"
    max_reconnect_attempts: int = 10
    reconnect_time_wait: float = 2.0


class NatsX:
    """Lightweight NATS JetStream client for workers."""

    def __init__(self, url: str = "nats://nats:4222"):
        self.url = url
        self.nc: Optional[nats.NATS] = None
        self.js: Optional[JetStreamContext] = None

    async def connect(self, opts: Optional[ConnectOptions] = None):
        """Connect to NATS with JetStream enabled."""
        if opts is None:
            opts = ConnectOptions(url=self.url)

        self.nc = await nats.connect(
            servers=[opts.url],
            max_reconnect_attempts=opts.max_reconnect_attempts,
            reconnect_time_wait=opts.reconnect_time_wait,
        )
        self.js = self.nc.jetstream()

    async def close(self):
        """Drain and close connection."""
        if self.nc:
            await self.nc.drain()
            await self.nc.close()

    async def ensure_stream(
        self,
        name: str,
        subjects: List[str],
        work_queue: bool = False,
        max_age_hours: int = 168,  # 7 days
    ):
        """Create or update a stream (idempotent)."""
        retention = RetentionPolicy.WORK_QUEUE if work_queue else RetentionPolicy.LIMITS

        await self.js.add_stream(
            StreamConfig(
                name=name,
                subjects=subjects,
                retention=retention,
                max_age=max_age_hours * 3600 * 1_000_000_000,  # nanoseconds
            )
        )

    async def publish(self, subject: str, payload: Any):
        """Publish a message with JetStream persistence."""
        if isinstance(payload, (dict, list)):
            data = json.dumps(payload).encode()
        elif isinstance(payload, str):
            data = payload.encode()
        elif isinstance(payload, bytes):
            data = payload
        else:
            data = json.dumps(payload).encode()

        await self.js.publish(subject, data)

    async def create_pull_consumer(self, stream: str, durable: str):
        """Create a durable pull consumer."""
        # Pull consumer will be created automatically on first pull_subscribe
        sub = await self.js.pull_subscribe(
            "",  # Empty subject subscribes to all subjects in stream
            durable=durable,
            stream=stream,
        )
        return PullSubscriber(sub)


class PullSubscriber:
    """Wrapper for JetStream pull subscription."""

    def __init__(self, sub):
        self.sub = sub

    async def fetch(self, batch: int = 1, timeout: float = 5.0) -> List:
        """Fetch up to batch messages."""
        try:
            msgs = await self.sub.fetch(batch, timeout=timeout)
            return msgs
        except TimeoutError:
            return []

    async def unsubscribe(self):
        """Close the subscription."""
        await self.sub.unsubscribe()


# Example usage:
async def example_producer():
    """Example: publish events to NATS."""
    client = NatsX()
    await client.connect()

    await client.ensure_stream("AGILE", ["agile.events"])

    await client.publish(
        "agile.events",
        {
            "event_id": "evt-123",
            "case_id": "c-001",
            "event_type": "CASE_CREATED",
            "ts": "2025-10-07T12:00:00Z",
        },
    )

    await client.close()


async def example_consumer():
    """Example: consume agent requests with durable consumer."""
    client = NatsX()
    await client.connect()

    await client.ensure_stream("AGENT_WORK", ["agent.requests"], work_queue=True)

    subscriber = await client.create_pull_consumer("AGENT_WORK", "agent_workers")

    while True:
        msgs = await subscriber.fetch(batch=1, timeout=10.0)
        for msg in msgs:
            payload = json.loads(msg.data)
            print(f"Processing task: {payload.get('task_id')}")

            # ... do work ...

            # Ack to remove from WorkQueue
            await msg.ack()

    await subscriber.unsubscribe()
    await client.close()


if __name__ == "__main__":
    # Run producer example
    asyncio.run(example_producer())



