#!/usr/bin/env python3
"""
Orchestrator E2E: trigger real deliberations and verify via gRPC + NATS.
- gRPC: ListCouncils, Deliberate
- NATS: await orchestration.* and agent.response.* events, print in realtime
"""
import asyncio
import os
import time
import sys
from datetime import datetime, timezone

import grpc
from nats.aio.client import Client as NATS

# Import generated stubs
sys.path.insert(0, "/app")
from gen import orchestrator_pb2, orchestrator_pb2_grpc  # type: ignore

ORCH_HOST = os.getenv("ORCHESTRATOR_HOST", "orchestrator.swe-ai-fleet.svc.cluster.local")
ORCH_PORT = os.getenv("ORCHESTRATOR_PORT", "50055")
ORCHESTRATOR_ADDRESS = f"{ORCH_HOST}:{ORCH_PORT}"
NATS_URL = os.getenv("NATS_URL", "nats://nats.swe-ai-fleet.svc.cluster.local:4222")
ROLE = os.getenv("ROLE", "DEV")
NUM_AGENTS = int(os.getenv("NUM_AGENTS", "3"))
TIMEOUT_SECS = int(os.getenv("TIMEOUT_SECS", "120"))


def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70 + "\n")


async def await_events(nc: NATS, timeout: int) -> bool:
    """Subscribe to orchestration.* and agent.response.* and wait for a completion event."""
    js = nc.jetstream()
    done = asyncio.Event()

    async def handler(msg):
        subj = msg.subject
        data = msg.data.decode("utf-8", errors="ignore")
        print(f"[{ts()}] [NATS] {subj}: {data[:300]}...")
        if subj.startswith("orchestration.deliberation.completed"):
            done.set()

    subs = []
    subs.append(await js.subscribe("orchestration.>", cb=handler))
    subs.append(await js.subscribe("agent.response.>", cb=handler))

    try:
        await asyncio.wait_for(done.wait(), timeout=timeout)
        return True
    except asyncio.TimeoutError:
        return False
    finally:
        for s in subs:
            try:
                await s.unsubscribe()
            except Exception:
                pass


async def main() -> int:
    print_header("🧪 Orchestrator E2E - Real Deliberations (Realtime NATS)")
    print(f"[{ts()}] Orchestrator: {ORCHESTRATOR_ADDRESS}")
    print(f"[{ts()}] NATS:         {NATS_URL}")

    # 1) gRPC connectivity
    print(f"\n[{ts()}] [Step 1] Checking gRPC connectivity to Orchestrator...")
    channel = grpc.insecure_channel(ORCHESTRATOR_ADDRESS)
    try:
        grpc.channel_ready_future(channel).result(timeout=10)
    except Exception as e:
        print(f"[{ts()}] ❌ Cannot connect to Orchestrator: {e}")
        return 1

    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)

    # 2) List councils
    print(f"[{ts()}] [Step 2] Listing councils...")
    try:
        resp = stub.ListCouncils(orchestrator_pb2.ListCouncilsRequest(include_agents=True))
        roles = [c.role for c in resp.councils]
        print(f"[{ts()}]    Councils: {roles}")
        if ROLE not in roles:
            print(f"[{ts()}] ⚠️ Expected role '{ROLE}' not in councils; proceeding anyway")
    except grpc.RpcError as e:
        print(f"[{ts()}] ❌ ListCouncils failed: {e.code()}: {e.details()}")
        return 1

    # 3) Connect to NATS
    print(f"[{ts()}] [Step 3] Connecting to NATS...")
    nc = NATS()
    try:
        await nc.connect(servers=[NATS_URL])
        print(f"[{ts()}]    ✅ Connected to NATS")
    except Exception as e:
        print(f"[{ts()}] ❌ NATS connection failed: {e}")
        return 1

    # 4) Trigger deliberation via gRPC
    print(f"[{ts()}] [Step 4] Triggering deliberation via gRPC...")
    task_description = (
        "Write a Python function to reverse a string with Unicode support; "
        "add type hints and a docstring."
    )
    constraints = orchestrator_pb2.TaskConstraints(
        rubric="Readable, documented, Unicode-safe",
        requirements=[
            "Use type hints",
            "Add docstring",
            "Handle empty string",
        ],
        timeout_seconds=120,
        max_iterations=1,
    )

    try:
        start = time.time()
        _ = stub.Deliberate(
            orchestrator_pb2.DeliberateRequest(
                task_description=task_description,
                role=ROLE,
                constraints=constraints,
                rounds=1,
                num_agents=NUM_AGENTS,
            )
        )
        duration = time.time() - start
        print(f"[{ts()}]    ✅ Deliberate returned in {duration:.1f}s")
    except grpc.RpcError as e:
        print(f"[{ts()}] ❌ Deliberate failed: {e.code()}: {e.details()}")
        await nc.drain()
        return 1

    # 5) Await orchestration events on NATS
    print(f"[{ts()}] [Step 5] Waiting for orchestration events (up to {TIMEOUT_SECS}s)...")
    ok = await await_events(nc, timeout=TIMEOUT_SECS)
    await nc.drain()

    if not ok:
        print(f"[{ts()}] ❌ Timed out waiting for orchestration messages")
        return 1

    print(f"\n[{ts()}] ✅ E2E passed: orchestration messages observed on NATS")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    raise SystemExit(exit_code)
